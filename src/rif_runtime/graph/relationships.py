from typing import Any

from .memory import GovernanceGraph


def actor_targets(graph: GovernanceGraph, actor: str) -> list[str]:
    if actor not in graph.graph:
        return []
    return list(graph.graph.successors(actor))


def denied_edges(graph: GovernanceGraph) -> list[dict[str, Any]]:
    return [
        {"actor": u, "target": v, **data}
        for u, v, data in graph.graph.edges(data=True)
        if data.get("decision") == "deny"
    ]
