def actor_targets(graph, actor: str):
    if actor not in graph.graph:
        return []
    return list(graph.graph.successors(actor))

def denied_edges(graph):
    return [
        {"actor": u, "target": v, **data}
        for u, v, data in graph.graph.edges(data=True)
        if data.get("decision") == "deny"
    ]
