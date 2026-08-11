from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph.memory import GovernanceGraph
from .schemas import Decision, PolicyDecision, Posture


class ReplayDecodeError(ValueError):
    """Raised when a decisions.jsonl line is not valid JSON."""

    def __init__(self, path: Path, line_no: int, message: str) -> None:
        self.path = path
        self.line_no = line_no
        super().__init__(f"invalid JSONL at {path}:{line_no}: {message}")


@dataclass
class RecoveredState:
    historical_decisions: int
    historical_denials: int
    graph_nodes: int
    graph_edges: int
    last_posture: str


class ReplayEngine:
    def __init__(self, decisions_path: str = "data/decisions.jsonl"):
        self.decisions_path = Path(decisions_path)

    def _rows(self) -> list[dict[str, Any]]:
        if not self.decisions_path.exists():
            return []

        rows: list[dict[str, Any]] = []
        for line_no, line in enumerate(
            self.decisions_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ReplayDecodeError(self.decisions_path, line_no, exc.msg) from exc
        return rows

    def replay_graph(self, rows: list[dict[str, Any]] | None = None) -> GovernanceGraph:
        """Rebuild the governance graph, optionally from an already-loaded log.

        Passing ``rows`` lets a caller that has already read the decision log
        reuse that snapshot instead of re-reading the file.
        """
        graph = GovernanceGraph()
        for row in self._rows() if rows is None else rows:
            graph.record_decision(self._decision_from_row(row))
        return graph

    def recover(self) -> RecoveredState:
        # Read the log once and derive both the counts and the graph from that
        # single snapshot: decisions.jsonl is appended to concurrently, so two
        # separate reads could report totals that disagree with each other.
        rows = self._rows()
        graph = self.replay_graph(rows)
        denials = sum(1 for row in rows if row.get("decision") == "deny")
        return RecoveredState(
            historical_decisions=len(rows),
            historical_denials=denials,
            graph_nodes=graph.summary()["nodes"],
            graph_edges=graph.summary()["edges"],
            last_posture=self._posture_from_denials(denials).value,
        )

    def _decision_from_row(self, row: dict[str, Any]) -> PolicyDecision:
        return PolicyDecision(
            decision=Decision(row["decision"]),
            actor=row["actor"],
            action=row["action"],
            target=row["target"],
            environment=row["environment"],
            posture=Posture(row["posture"]),
            reason=row["reason"],
            matched_rule=row["matched_rule"],
        )

    def _posture_from_denials(self, denials: int) -> Posture:
        if denials >= 20:
            return Posture.locked
        if denials >= 10:
            return Posture.restricted
        if denials >= 3:
            return Posture.elevated
        return Posture.normal
