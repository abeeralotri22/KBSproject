import networkx as nx
import json
import os

from new_graph_rules import (
    find_cycles, cycle_edges_entries_exits, structural_core_nodes,
    agency_score, convergence_score,
)

G = nx.read_graphml("../create&update/filtered_knowledge_graph.graphml")
id_to_label = {n: G.nodes[n].get("label", n) for n in G.nodes()}
label_to_id = {v: k for k, v in id_to_label.items()}

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

# feedback loops (cycles) are structurally important regardless of degree/betweenness,
# since a loop back to an earlier node is a core mechanism, not a side detail —
# and so is whatever meaningfully triggers it (entry) or continues from it (exit)
cycles = find_cycles(G, id_to_label)
cycle_edge_set, entry_edge_set, exit_edge_set = cycle_edges_entries_exits(G, id_to_label, cycles)
core_node_set = structural_core_nodes(cycles, entry_edge_set, exit_edge_set)
important |= core_node_set

# extract المكان and الزمان from node types
makan_nodes = [
    id_to_label[n] for n in G.nodes()
    if "مكان" in G.nodes[n].get("title", "")
]
zaman_nodes = [
    id_to_label[n] for n in G.nodes()
    if "زمان" in G.nodes[n].get("title", "")
]

agency = {label: agency_score(G, id_to_label, label_to_cluster, label_to_id, label)
          for label in out_degree}

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

# البطل: prioritize source nodes (in_degree=0) in the important set.
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

# المحور: highest disruption among remaining important nodes, excluding مكان nodes —
# but only if it's a genuine convergence point. A single-hero radial graph (several
# independent branches fanning out from one source, e.g. digestion, blood circulation)
# has no real "world everything happens around" — forcing a pivot onto whichever branch
# node scores highest disruption fabricates a role the graph doesn't structurally have.
# convergence_score (edges arriving from ≥2 *different* clusters, not just the hero's own
# branch) is what distinguishes a real hub (e.g. الخلية, fed by 3 independent clusters)
# from a mid-branch step that merely happens to fan back out to several children.
remaining = important - {hero}
remaining_non_place = remaining - \
    place_set if (remaining - place_set) else remaining
pivot_candidate = max(remaining_non_place,
                      key=lambda l: (disruption_scores.get(l, 0), in_degree.get(l, 0)))
pivot = pivot_candidate if convergence_score(
    G, id_to_label, label_to_cluster, label_to_id, pivot_candidate) >= 2 else None

# رئيسية: remaining important nodes with above-average agency among themselves.
# The threshold is relative to the candidate pool, with a floor of 1 (must reach at
# least one other cluster).
after_hero_pivot = remaining - ({pivot} if pivot else set())
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

# a node that's part of a feedback loop — or meaningfully triggers/continues one —
# is structurally core to the mechanism: never leave it in فرعية, even if its agency
# fell under the main-character threshold (hero/pivot are untouched: they already
# outrank رئيسية)
promoted = [l for l in secondary if l in core_node_set]
if promoted:
    secondary = [l for l in secondary if l not in core_node_set]
    main_chars = sorted(main_chars + promoted,
                         key=lambda l: disruption_scores.get(l, 0), reverse=True)

roles = {}
roles[hero] = "البطل"
if pivot:
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

cycles_out = [
    {
        "nodes":       cycle,
        "edges":       [list(e) for e in zip(cycle, cycle[1:] + cycle[:1])],
        "entry_edges": [list(e) for e in entry_edge_set if e[1] in cycle],
        "exit_edges":  [list(e) for e in exit_edge_set if e[0] in cycle],
    }
    for cycle in cycles
]

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
        "cycles":             cycles_out,
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