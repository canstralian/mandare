from __future__ import annotations

import networkx as nx

from ..schemas import PolicyDecision


class GovernanceGraph:
    def __init__(self) -> None:
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()

    def record_decision(self, decision: PolicyDecision) -> None:
        self.graph.add_node(decision.actor, type="actor")
        self.graph.add_node(decision.target, type="target")
        self.graph.add_edge(
            decision.actor,
            decision.target,
            decision=decision.decision.value,
            rule=decision.matched_rule,
            environment=decision.environment,
            posture=decision.posture.value,
            timestamp=decision.timestamp.isoformat(),
        )

    def summary(self) -> dict[str, int]:
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
        }
