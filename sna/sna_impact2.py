import networkx as nx
import json
import os

G = nx.read_graphml("../create&update/filtered_knowledge_graph.graphml")
id_to_label = {n: G.nodes[n].get("label", n) for n in G.nodes()}

with open("./results/sna_results.json", "r", encoding="utf-8") as f:
    sna = json.load(f)

out_degree = sna["Out Degree Centrality"]
in_degree = sna["In Degree Centrality"]
betweenness = sna["Betweenness Centrality"]
cut_nodes = set(sna["Cut Nodes"])
clusters = sna["Clusters"]

label_to_cluster = {}
for i, cluster in enumerate(clusters):
    for label in cluster:
        label_to_cluster[label] = i

# identify important nodes
avg_out = sum(out_degree.values()) / len(out_degree)
avg_in = sum(in_degree.values()) / len(in_degree)
avg_bet = sum(betweenness.values()) / len(betweenness)

important = {
    label for label in out_degree
    if (label in cut_nodes
        or out_degree.get(label, 0) > avg_out
        or in_degree.get(label, 0) > avg_in
        or betweenness.get(label, 0) > avg_bet)
}

# extract المكان and الزمان from node types
makan_nodes = [
    id_to_label[n] for n in G.nodes()
    if "مكان" in G.nodes[n].get("title", "")
]
zaman_nodes = [
    id_to_label[n] for n in G.nodes()
    if "زمان" in G.nodes[n].get("title", "")
]

# agency score


def agency_score(label):
    node_id = next(n for n, l in id_to_label.items() if l == label)
    reached = {label_to_cluster[id_to_label[v]]
               for _, v in G.out_edges(node_id)
               if id_to_label[v] in label_to_cluster}
    return len(reached)


agency = {label: agency_score(label) for label in out_degree}

# disruption simulation
total_edges = G.number_of_edges()
total_nodes = G.number_of_nodes()
total_pairs = total_nodes * (total_nodes - 1)
baseline_components = nx.number_weakly_connected_components(G)


def reachable_pairs(graph):
    return sum(len(nx.descendants(graph, n)) for n in graph.nodes())


baseline_reach = reachable_pairs(G)
os.makedirs("./results/removal_impact", exist_ok=True)
disruption_scores = {}

for node_id in G.nodes():
    label = id_to_label[node_id]
    if label not in important:
        continue
    lost_edges = [
        {"source": id_to_label[u], "target": id_to_label[v],
            "relation": d.get("label", "")}
        for u, v, d in G.edges(data=True)
        if u == node_id or v == node_id
    ]
    G_temp = G.copy()
    G_temp.remove_node(node_id)
    isolated = [id_to_label[n]
                for n in G_temp.nodes() if G_temp.degree(n) == 0]
    comp_after = nx.number_weakly_connected_components(G_temp)
    reach_after = reachable_pairs(G_temp)
    disruption = (
        len(lost_edges) / total_edges +
        (comp_after - baseline_components) +
        len(isolated) / total_nodes +
        (baseline_reach - reach_after) / total_pairs
    )
    disruption_scores[label] = round(disruption, 4)

    with open(f"./results/removal_impact/{label.strip().replace(' ', '_')}.json", "w", encoding="utf-8") as f:
        json.dump({
            "removed_node":        label,
            "disruption_score":    round(disruption, 4),
            "agency_score":        agency[label],
            "lost_edges_count":    len(lost_edges),
            "lost_edges":          lost_edges,
            "isolated_nodes":      isolated,
            "components_before":   baseline_components,
            "components_after":    comp_after,
            "graph_fragmented":    comp_after > baseline_components,
            "reachability_before": baseline_reach,
            "reachability_after":  reach_after,
            "reachability_loss":   baseline_reach - reach_after,
        }, f, ensure_ascii=False, indent=4)

#  assign roles (NEW RULES)

# البطل (NEW): prioritize source nodes (in_degree=0) in the important set.
# A source node has no incoming edges — it initiates the action, nothing acts on it first.
# If no source node is important, fall back to highest agency (original rule).
place_set = set(makan_nodes)
source_important = {l for l in important if in_degree.get(l, 0) == 0}
if source_important:
    hero = max(source_important,
               key=lambda l: (agency[l], out_degree.get(l, 0), disruption_scores.get(l, 0)))
else:
    hero = max(important,
               key=lambda l: (agency[l], out_degree.get(l, 0), disruption_scores.get(l, 0)))

# المحور (NEW): highest disruption among remaining important nodes, excluding مكان nodes.
# المحور is the structural world-pivot — most disruptive to remove — not necessarily the place.
remaining = important - {hero}
remaining_non_place = remaining - \
    place_set if (remaining - place_set) else remaining
pivot = max(remaining_non_place,
            key=lambda l: (disruption_scores.get(l, 0), in_degree.get(l, 0)))

# رئيسية (NEW): remaining important nodes with above-average agency among themselves.
# Old rule used a hardcoded "agency >= 2" — fails on small/linear graphs where no
# node reaches 2+ clusters, leaving رئيسية empty. Now the threshold is relative to
# the candidate pool, with a floor of 1 (must reach at least one other cluster).
after_hero_pivot = remaining - {pivot}
remaining_agencies = [agency[l] for l in after_hero_pivot]
avg_remaining_agency = (sum(remaining_agencies) /
                        len(remaining_agencies)) if remaining_agencies else 0
agency_threshold = max(1, avg_remaining_agency)

main_chars = sorted(
    [l for l in after_hero_pivot if agency[l] >= agency_threshold],
    key=lambda l: disruption_scores.get(l, 0), reverse=True
)

# فرعية: demoted important (below threshold) + all non-important
demoted = [l for l in after_hero_pivot if agency[l] < agency_threshold]
non_important = [id_to_label[n]
                 for n in G.nodes() if id_to_label[n] not in important]
secondary = demoted + non_important

roles = {}
roles[hero] = "البطل"
roles[pivot] = "المحور"
for l in main_chars:
    roles[l] = "رئيسية"
for l in secondary:
    roles[l] = "فرعية"

# print("\n=== الأدوار النهائية ===")
# for label, role in sorted(roles.items(),
#         key=lambda x: ["البطل","المحور","رئيسية","فرعية"].index(x[1])):
#     d = disruption_scores.get(label, "-")
#     a = agency[label]
#     src = "(source)" if in_degree.get(label, 0) == 0 else ""
#     print(f"  [{role}] {label}  (disruption={d}, agency={a}) {src}")

# print(f"\n=== المكان ({len(makan_nodes) if makan_nodes else 'غير محدد'}) ===")
# print(f"  {makan_nodes if makan_nodes else 'غير محدد'}")
# print(f"\n=== الزمان ({len(zaman_nodes) if zaman_nodes else 'غير محدد'}) ===")
# print(f"  {zaman_nodes if zaman_nodes else 'غير محدد'}")

with open("./results/criticality_scores.json", "w", encoding="utf-8") as f:
    json.dump({
        "roles":              roles,
        "disruption_scores":  disruption_scores,
        "agency_scores":      agency,
        "important_nodes":    list(important),
        "hero":               hero,
        "pivot":              pivot,
        "main":               main_chars,
        "secondary":          secondary,
    }, f, ensure_ascii=False, indent=4)

story_elements = {
    "الشخصيات": {
        "البطل":   hero,
        "المحور":  pivot,
        "رئيسية": main_chars,
        "فرعية":  secondary,
    },
    "المكان": makan_nodes if len(makan_nodes) > 1 else (makan_nodes[0] if makan_nodes else "غير محدد"),
    "الزمان": zaman_nodes if len(zaman_nodes) > 1 else (zaman_nodes[0] if zaman_nodes else "غير محدد"),
}

with open("./results/story_elements.json", "w", encoding="utf-8") as f:
    json.dump(story_elements, f, ensure_ascii=False, indent=4)

print("\nsaved to results/removal_impact/ && results/criticality_scores.json && results/story_elements.json")
