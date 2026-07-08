import networkx as nx


class GovernanceGraph:
    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def record_decision(self, decision):
        self.graph.add_node(decision.actor, type="actor")
        self.graph.add_node(decision.target, type="target")
        self.graph.add_edge(
            decision.actor,
            decision.target,
            decision=decision.decision.value
            if hasattr(decision.decision, "value")
            else decision.decision,
            rule=decision.matched_rule,
            environment=decision.environment,
            posture=decision.posture.value
            if hasattr(decision.posture, "value")
            else decision.posture,
            timestamp=decision.timestamp.isoformat(),
        )

    def summary(self):
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
        }
