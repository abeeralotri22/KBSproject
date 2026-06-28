# write nodeid instead of labels
# import networkx as nx
# import json

# G = nx.read_graphml("knowledge_graph.graphml")

# # run all SNA
# degree = nx.degree_centrality(G)
# out_degree = nx.out_degree_centrality(G)
# betweenness = nx.betweenness_centrality(G)
# clusters = [list(c)
#             for c in nx.community.louvain_communities(G.to_undirected())]
# cuts = list(nx.articulation_points(G.to_undirected()))
# density = nx.density(G)

# try:
#     cycle = nx.find_cycle(G)
#     cycles = cycle
# except nx.NetworkXNoCycle:
#     cycles = "None"

# # build output dict
# results = {
#     "Degree Centrality": degree,
#     "Out Degree Centrality": out_degree,
#     "Betweenness Centrality": betweenness,
#     "Cut Nodes": cuts,
#     "Clusters": clusters,
#     "Density": density,
#     "Cycles": cycles
# }

# # save to file with Arabic support
# with open("sna_results.json", "w", encoding="utf-8") as f:
#     json.dump(results, f, ensure_ascii=False, indent=4)

# print("saved in sna_results.json")


import networkx as nx
import json

G = nx.read_graphml("../knowledge_graph.graphml")
# G = nx.read_graphml("wiki_extracted_knowledge_graph.graphml")
# build id → label map
id_to_label = {node: G.nodes[node].get("label", node) for node in G.nodes()}


# convert id to label
def to_labels(d):
    return {id_to_label[k]: v for k, v in d.items()}


#  SNA
degree = to_labels(nx.degree_centrality(G))
out_degree = to_labels(nx.out_degree_centrality(G))
in_degree = to_labels(nx.in_degree_centrality(G))
betweenness = to_labels(nx.betweenness_centrality(G))
pagerank = to_labels(nx.pagerank(G))
cuts = [id_to_label[n] for n in nx.articulation_points(G.to_undirected())]
clusters = [[id_to_label[n] for n in c]
            for c in nx.community.louvain_communities(G.to_undirected())]
density = nx.density(G)

try:
    cycle = [(id_to_label[u], id_to_label[v]) for u, v, *_ in nx.find_cycle(G)]
except nx.NetworkXNoCycle:
    cycle = "None"

# try:
#     cycle = nx.find_cycle(G)
#     cycles = cycle
# except nx.NetworkXNoCycle:
#     cycles = "None"

# build output dict
results = {
    "Degree Centrality": degree,
    "In Degree Centrality": in_degree,
    "Out Degree Centrality": out_degree,
    "Betweenness Centrality": betweenness,
    "Pagerank": pagerank,
    "Cut Nodes": cuts,
    "Clusters": clusters,
    "Density": density,
    "Cycles": cycle
}


with open("./results/sna_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=4)

print("saved in sna_results.json")
