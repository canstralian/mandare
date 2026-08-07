from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .governance.posture import posture_for_denials
from .graph.memory import GovernanceGraph
from .schemas import PolicyDecision


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
        import json

        if not self.decisions_path.exists():
            return []

        rows: list[dict[str, Any]] = []
        for line in self.decisions_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
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
            last_posture=posture_for_denials(denials).value,
        )

    def _decision_from_row(self, row: dict[str, Any]) -> PolicyDecision:
        # model_validate preserves persisted timestamps (and accepts both ISO
        # and the legacy space-separated form from json.dumps(..., default=str)).
        # Manual field picking dropped timestamp and minted a fresh now().
        return PolicyDecision.model_validate(row)
