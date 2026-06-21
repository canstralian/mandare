from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph.memory import GovernanceGraph
from .schemas import Decision, PolicyDecision, Posture


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

    def replay_graph(self) -> GovernanceGraph:
        graph = GovernanceGraph()
        for row in self._rows():
            graph.record_decision(self._decision_from_row(row))
        return graph

    def recover(self) -> RecoveredState:
        rows = self._rows()
        graph = self.replay_graph()
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
