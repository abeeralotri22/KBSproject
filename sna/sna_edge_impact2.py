import networkx as nx
import json
import os

# هاد عامل حالو جينيرالايزد
G = nx.read_graphml("../create&update/filtered_knowledge_graph.graphml")
id_to_label = {n: G.nodes[n].get("label", n) for n in G.nodes()}
label_to_id = {v: k for k, v in id_to_label.items()}

with open("./results/criticality_scores.json", "r", encoding="utf-8") as f:
    crit = json.load(f)

hero = crit["hero"]
pivot = crit["pivot"]
important = set(crit["important_nodes"])

hero_id = label_to_id[hero]
pivot_id = label_to_id[pivot]

conflict_actors = [
    X for X in (important - {hero, pivot})
    if G.has_edge(label_to_id[X], pivot_id)
]

conflicts = []
conflict_edges = []

for X in conflict_actors:
    X_id = label_to_id[X]
    reactors = [
        Y for Y in important
        if Y != X and G.has_edge(label_to_id[Y], X_id)
    ]

    if hero in reactors:
        narrative = "فعل_ورد_فعل"
    elif reactors:
        narrative = "فعل_ورد_فعل_غير_مباشر"
    else:
        narrative = "تنافس"

    conflicts.append({
        "actor":          X,
        "reactors":       reactors,
        "narrative_type": narrative,
    })

    conflict_edges.append({
        "source": X, "target": pivot,
        "src_id": X_id, "tgt_id": pivot_id,
        "relation": G.edges[X_id, pivot_id].get("label", ""),
        "type": "فعل",
    })
    for Y in reactors:
        Y_id = label_to_id[Y]
        conflict_edges.append({
            "source": Y, "target": X,
            "src_id": Y_id, "tgt_id": X_id,
            "relation": G.edges[Y_id, X_id].get("label", ""),
            "type": "رد فعل",
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

with open("./results/edge_impact_summary.json", "w", encoding="utf-8") as f:
    json.dump({
        "conflicts":           conflicts,
        "edges_by_disruption": results,
    }, f, ensure_ascii=False, indent=4)

print("\n saved to results/edge_impact/ && results/edge_impact_summary.json")
