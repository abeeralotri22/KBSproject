import networkx as nx
import json
import os

from new_graph_rules import (
    find_cycles, cycle_edges_entries_exits, structural_core_nodes,
    agency_score, convergence_score,
)
from archetype import classify_archetype, longest_path_roles, classify_chain_subtype

G = nx.read_graphml("../create&update/filtered_knowledge_graph.graphml")
id_to_label = {n: G.nodes[n].get("label", n) for n in G.nodes()}
label_to_id = {v: k for k, v in id_to_label.items()}
# the place-type exclusion below (place_set) was built for science lessons,
# where a place is usually just an incidental location reference, not the
# actual subject. In history/geography lessons the place itself is often
# what the narrative converges on, so the exclusion is gated on this
# domain tag from the source lesson — defaults to science when a lesson doesn't set one.
lesson_domain = G.graph.get("subject", "علوم")

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

# archetype: "hub" (branching/descriptive) uses
# cut-node/cluster centrality. "chain" (linear process or
# causal chain) makes those metrics degenerate
# (almost every node becomes a cut node regardless of size), so it's handled
# by longest_path_roles instead
archetype = classify_archetype(G)
chain_info = longest_path_roles(
    G, id_to_label) if archetype == "chain" else None
if chain_info is None:
    archetype = "hub"
chain_subtype = classify_chain_subtype(
    G, label_to_id, chain_info) if chain_info else None

cycles = find_cycles(G, id_to_label)
cycle_edge_set, entry_edge_set, exit_edge_set = cycle_edges_entries_exits(
    G, id_to_label, cycles)
core_node_set = structural_core_nodes(cycles, entry_edge_set, exit_edge_set)

if archetype == "hub":
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
    important |= core_node_set
else:
    important = (set(chain_info["spine"]) | set(chain_info["resolutions"])
                 | set(chain_info["extra_triggers"]))
    for branch in chain_info["branches"]:
        important |= set(branch["nodes"])

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


if archetype == "hub":
    # البطل: whoever is most central among the important nodes — highest
    # agency (reaches the most distinct clusters), not whoever happens to
    # be mentioned first. in_degree==0 used to be a hard requirement, but
    # for descriptive text the first-mentioned node is often just a
    # locating reference , not the actual subject
    #  that produced wrong heroes on several test graphs.
    place_set = set(makan_nodes) if lesson_domain == "علوم" else set()
    hero = max(important,
               key=lambda l: (agency[l], out_degree.get(l, 0), disruption_scores.get(l, 0)))

    # المحور: a convergence point — fed by edges from >=2 distinct clusters,
    # not just the hero's own branch. Still restricted to "important" nodes
    # (must be independently significant — a minor node shouldn't qualify
    # just by having two predecessors), but now every important node is
    # checked instead of only the single highest-disruption one: that used
    # to mean a genuine convergence point went untested whenever it wasn't
    # also the single most-disruptive important node.
    remaining = important - {hero}
    pivot_pool_space = remaining - \
        place_set if (remaining - place_set) else remaining
    pivot_scores = {
        l: convergence_score(G, id_to_label, label_to_cluster, label_to_id, l)
        for l in pivot_pool_space
    }
    pivot_pool = [l for l in pivot_pool_space if pivot_scores[l] >= 2]
    pivot = max(
        pivot_pool,
        key=lambda l: (pivot_scores[l], disruption_scores.get(
            l, 0), in_degree.get(l, 0))
    ) if pivot_pool else None
    if pivot:
        important = important | {pivot}

    # رئيسية: remaining important nodes with above-average agency among themselves
    #  with a floor of 1 cluster reach
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

    # a node that's part of a cycle,  or meaningfully triggers/continues one
    promoted = [l for l in secondary if l in core_node_set]
    if promoted:
        secondary = [l for l in secondary if l not in core_node_set]
        main_chars = sorted(main_chars + promoted,
                            key=lambda l: disruption_scores.get(l, 0), reverse=True)
else:
    # chain archetype: roles come straight from the causal spine
    # (trigger -> stages -> outcome) instead of centrality/clusters.
    hero = chain_info["trigger"]
    pivot = chain_info["outcome"]
    main_chars = list(chain_info["stages"])
    secondary = list(chain_info["resolutions"]) + \
        list(chain_info["side_effects"])

if archetype == "hub":
    roles = {hero: "البطل"}
    if pivot:
        roles[pivot] = "المحور"
    for l in main_chars:
        roles[l] = "رئيسية"
    for l in secondary:
        roles[l] = "فرعية"
elif chain_subtype == "causal":
    roles = {hero: "المحفز"}
    if pivot:
        roles[pivot] = "حل" if chain_info["outcome_is_resolution"] else "النتيجة"
    for l in main_chars:
        roles[l] = "مرحلة"
    for branch in chain_info["branches"]:
        roles[branch["trigger"]
              ] = "المحفز" if branch["trigger_is_independent"] else "مرحلة"
        for l in branch["stages"]:
            roles[l] = "مرحلة"
        roles[branch["outcome"]
              ] = "حل" if branch["outcome_is_resolution"] else "النتيجة"
    for l in chain_info["extra_triggers"]:
        roles[l] = "المحفز"
    for l in chain_info["resolutions"]:
        roles[l] = "حل"
    for l in chain_info["side_effects"]:
        roles[l] = "أثر_جانبي"
else:  # sequence: linear/ordered but not cause->effect
    roles = {hero: "البداية"}
    if pivot:
        roles[pivot] = "الخاتمة"
    for l in main_chars:
        roles[l] = "خطوة"
    for branch in chain_info["branches"]:
        roles[branch["trigger"]
              ] = "البداية" if branch["trigger_is_independent"] else "خطوة"
        for l in branch["stages"]:
            roles[l] = "خطوة"
        roles[branch["outcome"]] = "الخاتمة"
    for l in chain_info["extra_triggers"]:
        roles[l] = "البداية"
    for l in chain_info["resolutions"]:
        roles[l] = "فرعي"
    for l in chain_info["side_effects"]:
        roles[l] = "فرعي"

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
        "archetype":          archetype,
        "chain_subtype":      chain_subtype,
        "chain_details":      chain_info,
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

elements_by_role = {}
for label, role in roles.items():
    elements_by_role.setdefault(role, []).append(label)

story_elements = {
    "archetype": archetype,
    "chain_subtype": chain_subtype,
    "العناصر": elements_by_role,
    "المكان": makan_nodes if len(makan_nodes) > 1 else (makan_nodes[0] if makan_nodes else "غير محدد"),
    "الزمان": zaman_nodes if len(zaman_nodes) > 1 else (zaman_nodes[0] if zaman_nodes else "غير محدد"),
}

with open("./results/story_elements.json", "w", encoding="utf-8") as f:
    json.dump(story_elements, f, ensure_ascii=False, indent=4)

print("\nsaved to results/removal_impact/ && results/criticality_scores.json && results/story_elements.json")
