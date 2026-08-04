from typing import Any

from .memory import GovernanceGraph


def actor_targets(graph: GovernanceGraph, actor: str) -> list[str]:
    """
    Return the direct targets associated with an actor in the governance graph.
    
    Parameters:
    	actor (str): The actor whose direct targets to retrieve.
    
    Returns:
    	list[str]: The actor's direct target nodes, or an empty list if the actor is absent.
    """
    if actor not in graph.graph:
        return []
    return list(graph.graph.successors(actor))


def denied_edges(graph: GovernanceGraph) -> list[dict[str, Any]]:
    """
    Return all denied edges in the governance graph.
    
    Parameters:
    	graph (GovernanceGraph): The graph whose edges are examined.
    
    Returns:
    	list[dict[str, Any]]: Edge records containing each denied edge's actor, target, and associated data.
    """
    return [
        {"actor": u, "target": v, **data}
        for u, v, data in graph.graph.edges(data=True)
        if data.get("decision") == "deny"
    ]
