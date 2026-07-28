from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .governance.posture import posture_for_denials
from .graph.memory import GovernanceGraph
from .paths import DECISIONS_FILE, data_path
from .schemas import Decision, PolicyDecision, Posture
from .storage.jsonl import JsonlStore


@dataclass
class RecoveredState:
    historical_decisions: int
    historical_denials: int
    graph_nodes: int
    graph_edges: int
    last_posture: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReplayEngine:
    def __init__(self, decisions_path: str | Path | None = None) -> None:
        # Reuse JsonlStore rather than re-implementing JSONL parsing, so replay
        # and the live append path agree on the on-disk format.
        self.store = JsonlStore(decisions_path or data_path(DECISIONS_FILE))

    def replay_graph(self) -> GovernanceGraph:
        graph = GovernanceGraph()
        for row in self.store.read_all():
            graph.record_decision(self._decision_from_row(row))
        return graph

    def recover(self) -> RecoveredState:
        # Single read of the log; the graph is rebuilt from those same rows so
        # a growing decisions.jsonl is not scanned twice per recovery.
        rows = self.store.read_all()
        graph = GovernanceGraph()
        denials = 0
        for row in rows:
            graph.record_decision(self._decision_from_row(row))
            if row.get("decision") == Decision.deny.value:
                denials += 1

        summary = graph.summary()
        return RecoveredState(
            historical_decisions=len(rows),
            historical_denials=denials,
            graph_nodes=summary["nodes"],
            graph_edges=summary["edges"],
            last_posture=posture_for_denials(denials).value,
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
