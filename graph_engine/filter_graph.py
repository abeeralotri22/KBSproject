import networkx as nx

FILTERED_EDGE_TYPES = {"مثل"}

G = nx.read_graphml("create&update/knowledge_graph.graphml")

edges_to_remove = [
    (u, v) for u, v, d in G.edges(data=True)
    if d.get("label", "").strip() in FILTERED_EDGE_TYPES
]

G.remove_edges_from(edges_to_remove)

nx.write_graphml(G, "create&update/filtered_knowledge_graph.graphml")

print(f"removed {len(edges_to_remove)} '{'/'.join(FILTERED_EDGE_TYPES)}' edges")
print("saved to create&update/filtered_knowledge_graph.graphml")
