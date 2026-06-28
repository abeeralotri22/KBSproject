import networkx as nx
import json
import os

G = nx.read_graphml("../create&update/knowledge_graph.graphml")
id_to_label = {n: G.nodes[n].get("label", n) for n in G.nodes()}
label_to_id = {v: k for k, v in id_to_label.items()}

with open("./results/criticality_scores.json", "r", encoding="utf-8") as f:
    crit = json.load(f)

hero = crit["hero"]
pivot = crit["pivot"]
main = set(crit["main"])

hero_id = label_to_id[hero]
pivot_id = label_to_id[pivot]

#  find conflict nodes and their edges
# X must be رئيسية AND (X → المحور) AND (البطل → X)
conflict_nodes = [
    X for X in main
    if G.has_edge(label_to_id[X], pivot_id) and G.has_edge(hero_id, label_to_id[X])
]

conflict_edges = []
for X in conflict_nodes:
    X_id = label_to_id[X]
    conflict_edges.append({
        "source":   X,
        "target":   pivot,
        "src_id":   X_id,
        "tgt_id":   pivot_id,
        "relation": G.edges[X_id, pivot_id].get("label", ""),
        "type":     "فعل",
    })
    conflict_edges.append({
        "source":   hero,
        "target":   X,
        "src_id":   hero_id,
        "tgt_id":   X_id,
        "relation": G.edges[hero_id, X_id].get("label", ""),
        "type":     "رد فعل",
    })

#  baseline metrics
baseline_components = nx.number_weakly_connected_components(G)


def reachable_pairs(graph):
    return sum(len(nx.descendants(graph, n)) for n in graph.nodes())


baseline_reach = reachable_pairs(G)

# removing each conflict edge
os.makedirs("./results/edge_impact", exist_ok=True)

results = []

for edge in conflict_edges:
    src_id = edge["src_id"]
    tgt_id = edge["tgt_id"]

    G_temp = G.copy()
    G_temp.remove_edge(src_id, tgt_id)

    comp_after = nx.number_weakly_connected_components(G_temp)
    reach_after = reachable_pairs(G_temp)
    isolated = [id_to_label[n]
                for n in G_temp.nodes() if G_temp.degree(n) == 0]
    reach_loss = baseline_reach - reach_after

    try:
        still_reachable = nx.has_path(G_temp, src_id, tgt_id)
    except (nx.NetworkXError, nx.exception.NodeNotFound):
        still_reachable = False

    tgt_in_degree = G.in_degree(tgt_id)
    src_out_degree = G.out_degree(src_id)

    path_broken = 0 if still_reachable else 1
    target_dependency = round(1 / tgt_in_degree if tgt_in_degree > 0 else 1, 4)
    source_influence = round(
        1 / src_out_degree if src_out_degree > 0 else 1, 4)
    proportional_reach = round(
        reach_loss / baseline_reach if baseline_reach > 0 else 0, 4)
    fragmentation = comp_after - baseline_components

    disruption = round(
        path_broken + target_dependency + source_influence +
        proportional_reach + fragmentation,
        4
    )

    result = {
        "source":                      edge["source"],
        "target":                      edge["target"],
        "relation":                    edge["relation"],
        "conflict_type":               edge["type"],
        "disruption_score":            disruption,
        "path_broken": not still_reachable,
        "target_dependency":           target_dependency,
        "source_influence":            source_influence,
        "proportional_reach_loss":     proportional_reach,
        "graph_fragmented":            comp_after > baseline_components,
        "reachability_before":         baseline_reach,
        "reachability_after":          reach_after,
        "reachability_loss":           reach_loss,
        "isolated_nodes":              isolated,
    }
    results.append(result)

    fname = f"{edge['type']}_{edge['source'].strip().replace(' ', '_')}_to_{edge['target'].strip().replace(' ', '_')}.json"
    with open(f"./results/edge_impact/{fname}", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

results.sort(key=lambda x: -x["disruption_score"])

# print(f"=== تأثير إزالة وصلات الصراع ({len(results)}) ===")
# for r in results:
#     broken = "✗ مقطوع" if r["path_broken"] else "✓ بديل موجود"
#     print(
#         f"  [{r['conflict_type']}] {r['source']} → {r['target']}  ({r['relation']})")
#     print(
#         f"    disruption={r['disruption_score']}  {broken}  reach_loss={r['reachability_loss']}")

with open("./results/edge_impact_summary.json", "w", encoding="utf-8") as f:
    json.dump({
        "conflict_nodes":       conflict_nodes,
        "edges_by_disruption":  results,
    }, f, ensure_ascii=False, indent=4)

print("\n✓ saved to results/edge_impact/ && results/edge_impact_summary.json")
