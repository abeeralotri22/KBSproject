import networkx as nx
import json
import os


G = nx.read_graphml("../knowledge_graph.graphml")
id_to_label = {n: G.nodes[n].get("label", n) for n in G.nodes()}

with open("./results/sna_results.json", "r", encoding="utf-8") as f:
    sna = json.load(f)

out_degree = sna["Out Degree Centrality"]
in_degree = sna["In Degree Centrality"]
betweenness = sna["Betweenness Centrality"]
cut_nodes = set(sna["Cut Nodes"])
clusters = sna["Clusters"]  # list of lists of labels

# build label → cluster_index map
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

# print(f"العقد المهمة ({len(important)}): {important}")


#  agency score (cross-cluster reach)
# counts how many distinct clusters a node's out-edges reach
def agency_score(label):
    node_id = next(n for n, l in id_to_label.items() if l == label)
    reached = {label_to_cluster[id_to_label[v]]
               for _, v in G.out_edges(node_id)
               if id_to_label[v] in label_to_cluster}
    return len(reached)


agency = {label: agency_score(label) for label in out_degree}

# print("\n===cross-cluster reach ===")
# for label, score in sorted(agency.items(), key=lambda x: -x[1]):
#     marker = " ◄" if label in important else ""
#     print(f"  {label}: {score}{marker}")

#  disruption score شو مقدار الخلل يلي بتعملو ازالة العقدة
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

# assign roles
# البطل: highest agency among important (tiebreak: out_degree, then disruption)
hero = max(important,
           key=lambda l: (agency[l], out_degree.get(l, 0), disruption_scores.get(l, 0)))

# المحور: highest in_degree among important excluding hero (tiebreak: disruption)
remaining = important - {hero}
pivot = max(remaining,
            key=lambda l: (in_degree.get(l, 0), disruption_scores.get(l, 0)))

# شخصيات رئيسية: remaining important nodes that reach ≥ 2 clusters
after_hero_pivot = remaining - {pivot}
main_chars = sorted([l for l in after_hero_pivot if agency[l] >= 2],
                    key=lambda l: disruption_scores.get(l, 0), reverse=True)

# شخصيات فرعية: remaining important with agency < 2 + all non-important
demoted = [l for l in after_hero_pivot if agency[l] < 2]
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

# output
# print("\n=== الأدوار النهائية ===")
# for label, role in sorted(roles.items(), key=lambda x: ["البطل", "المحور", "رئيسية", "فرعية"].index(x[1])):
#     d = disruption_scores.get(label, "-")
#     a = agency[label]
#     print(f"  [{role}] {label}  (disruption={d}, agency={a})")

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

print("\n saved to results/removal_impact/ && results/criticality_scores.json")

#  story elements
# الزمان: not derivable from graph structure 

# المكان: المحور node (highest in-degree = the world everything happens inside)
# الأزمة: the removal scenario of the البطل reveals the story conflict

hero_impact = {}
if hero in disruption_scores:
    hero_impact_file = f"./results/removal_impact/{hero.strip().replace(' ', '_')}.json"
    if os.path.exists(hero_impact_file):
        with open(hero_impact_file, "r", encoding="utf-8") as f:
            hero_impact = json.load(f)

story_elements = {
    "الشخصيات": {
        "البطل":    hero,
        "المحور":   pivot,
        "رئيسية":  main_chars,
        "فرعية":   secondary,
    },
    "المكان": {
        "العقدة":   pivot,
        "المصدر":   "المحور ، العقدة ذات أعلى وصلات داخلة اليها ، كل شيء يحدث داخلها أو حولها",
    },
    # "الزمان": {
    #     "القيمة":   "غير محدد من الرسم البياني",
    #     "الملاحظة": "الزمان لا يمكن استخلاصه من بنية الرسم البياني — يتطلب معالجة لغوية على النص الأصلي",
    # },
    # "الأزمة": {
    #     "المحرك":        hero,
    #     "disruption_score": disruption_scores.get(hero, None),
    #     "agency_score":     agency.get(hero, None),
    #     "العلاقات_المفقودة": hero_impact.get("lost_edges", []),
    #     "العقد_المعزولة":    hero_impact.get("isolated_nodes", []),
    #     "تفتت_الرسم_البياني": hero_impact.get("graph_fragmented", None),
    # },
}

with open("./results/story_elements.json", "w", encoding="utf-8") as f:
    json.dump(story_elements, f, ensure_ascii=False, indent=4)

print("saved to results/story_elements.json")
