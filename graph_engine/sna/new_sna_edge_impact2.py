import networkx as nx
import json
import os

from new_graph_rules import find_cycles, cycle_edges_entries_exits, classify_narrative_conflicts

# هاد عامل حالو جينيرالايزد
G = nx.read_graphml("../create&update/filtered_knowledge_graph.graphml")
id_to_label = {n: G.nodes[n].get("label", n) for n in G.nodes()}
label_to_id = {v: k for k, v in id_to_label.items()}

with open("./results/criticality_scores.json", "r", encoding="utf-8") as f:
    crit = json.load(f)

hero = crit["hero"]
pivot = crit["pivot"]
roles = crit["roles"]
archetype = crit.get("archetype", "hub")
chain_info = crit.get("chain_details")
chain_subtype = crit.get("chain_subtype")
spine_edge_type = "مسار_سببي" if chain_subtype == "causal" else "تسلسل"
resolution_edge_type = "حل" if chain_subtype == "causal" else "إضافة"

conflict_edges = []
seen_edges = set()

# نحسب وصلات الحلقة اولا ان وجدت
cycles = find_cycles(G, id_to_label)
cycle_edge_set, entry_edge_set, exit_edge_set = cycle_edges_entries_exits(
    G, id_to_label, cycles)

# تصنيف كل وصلة حلقة/دخول/خروج حسب نوعها
for source, target in sorted(cycle_edge_set | entry_edge_set | exit_edge_set):
    key = (source, target)
    seen_edges.add(key)
    if key in cycle_edge_set:
        edge_type = "حلقة"
    elif key in entry_edge_set:
        edge_type = "دخول"
    else:
        edge_type = "امتداد"
    conflict_edges.append({
        "source": source, "target": target,
        "src_id": label_to_id[source], "tgt_id": label_to_id[target],
        "relation": G.edges[label_to_id[source], label_to_id[target]].get("label", ""),
        "type": edge_type,
    })

if archetype == "chain":
    # no adversary here — the "action" is the causal spine itself, and
    # any resolution edge ( rest -> fatigue) is a mitigation, not a fight.
    for source, target in chain_info["spine_edges"]:
        key = (source, target)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        conflict_edges.append({
            "source": source, "target": target,
            "src_id": label_to_id[source], "tgt_id": label_to_id[target],
            "relation": G.edges[label_to_id[source], label_to_id[target]].get("label", ""),
            "type": spine_edge_type,
        })
    for source, target in chain_info["resolution_edges"]:
        key = (source, target)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        conflict_edges.append({
            "source": source, "target": target,
            "src_id": label_to_id[source], "tgt_id": label_to_id[target],
            "relation": G.edges[label_to_id[source], label_to_id[target]].get("label", ""),
            "type": resolution_edge_type,
        })
    for branch in chain_info["branches"]:
        for source, target in branch["edges"]:
            key = (source, target)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            conflict_edges.append({
                "source": source, "target": target,
                "src_id": label_to_id[source], "tgt_id": label_to_id[target],
                "relation": G.edges[label_to_id[source], label_to_id[target]].get("label", ""),
                "type": spine_edge_type,
            })
    for source, target in chain_info["extra_trigger_edges"]:
        key = (source, target)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        conflict_edges.append({
            "source": source, "target": target,
            "src_id": label_to_id[source], "tgt_id": label_to_id[target],
            "relation": G.edges[label_to_id[source], label_to_id[target]].get("label", ""),
            "type": spine_edge_type,
        })
    for source, target in chain_info["fork_entry_edges"]:
        key = (source, target)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        conflict_edges.append({
            "source": source, "target": target,
            "src_id": label_to_id[source], "tgt_id": label_to_id[target],
            "relation": G.edges[label_to_id[source], label_to_id[target]].get("label", ""),
            "type": spine_edge_type,
        })
else:
    # البطل ما بيتصارع مع المحور، والصراع الحقيقي بس مع اللي عندو وصلة مباشرة مع البطل
    for edge in classify_narrative_conflicts(G, id_to_label, label_to_id, roles, hero, pivot):
        key = (edge["source"], edge["target"])
        if key in seen_edges:
            continue
        seen_edges.add(key)
        conflict_edges.append(edge)

# تجميع الوصلات حسب نوعها لعرضها بشكل ملخّص
conflicts_by_type = {}
for edge in conflict_edges:
    conflicts_by_type.setdefault(edge["type"], []).append(
        {"source": edge["source"], "target": edge["target"], "relation": edge["relation"]})

conflicts = [{"type": t, "edges": edges}
             for t, edges in conflicts_by_type.items()]
# إضافة الحلقة نفسها كعنصر مستقل بالملخّص إن وُجدت
if cycles:
    conflicts.append({
        "cycles":         cycles,
        "narrative_type": "feedback loop",
    })

#  baseline metrics
baseline_components = nx.number_weakly_connected_components(G)


def reachable_pairs(graph):
    return sum(len(nx.descendants(graph, n)) for n in graph.nodes())


baseline_reach = reachable_pairs(G)
# nodes already disconnected before any edge is touched ( a node whose
# only connection was a "مثل" ) must be
# excluded below — otherwise they show up as "isolated" after removing
# every single edge in the graph, which isn't a consequence of that edge at
# all, just pre-existing noise.
baseline_isolated = {n for n in G.nodes() if G.degree(n) == 0}

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
                for n in G_temp.nodes()
                if G_temp.degree(n) == 0 and n not in baseline_isolated]
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
