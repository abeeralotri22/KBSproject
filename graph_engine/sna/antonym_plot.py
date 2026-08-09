import networkx as nx
import json
import os
from pyvis.network import Network
from antonym_lexicon import negate_relation, negate_by_type


with open("./results/criticality_scores.json", "r", encoding="utf-8") as f:
    crit = json.load(f)

if crit.get("archetype") != "hub":
    raise SystemExit(
        f"antonym_plot.py only applies to hub archetype — this graph is "
        f"archetype={crit.get('archetype')!r} (use antonym_chain.py for chain graphs)"
    )

hero = crit["hero"]
pivot = crit["pivot"]

with open("./results/sna_plot_graph_filtered.json", "r", encoding="utf-8") as f:
    plot = json.load(f)

roles = {n["label"]: n["role"] for n in plot["nodes"]}
significant_nodes = set(roles.keys())

# a broken edge's SOURCE concept gets negated too when it's a genuine
# event/action node , not just its
# relation, Stable entities (organs, places...)
# keep their label; only their outgoing relations negate.
raw = nx.read_graphml("../create&update/filtered_knowledge_graph.graphml")
label_to_type = {d.get("label", "").strip(): d.get("title", "").strip()
                 for _, d in raw.nodes(data=True)}
negated_source_labels = {}


def negated_source(label):
    if label not in negated_source_labels:
        negated_source_labels[label] = negate_by_type(
            label, label_to_type.get(label.strip(), ""))
    return negated_source_labels[label]


# every edge in the filtered Plot IS the breakable set already — except a
# purely positional/locative relation (خلفها, فيها مقابل ), which
# negate_relation deliberately leaves unchanged.  so they go to intact instead of broken.
antonym_edges = []
positional_edges = []
for e in plot["edges"]:
    negated = negate_relation(e["relation"])
    if negated.strip() == e["relation"].strip():
        positional_edges.append({
            "source": e["source"],
            "target": e["target"],
            "original_relation": e["relation"],
            "relation": negated,
            "conflict_type": e["conflict_type"],
        })
    else:
        antonym_edges.append({
            "source": negated_source(e["source"]),
            "original_source": e["source"],
            "target": e["target"],
            "original_relation": e["relation"],
            "relation": negated,
            "conflict_type": e["conflict_type"],
        })

# the one edge deliberately absent from the filtered Plot — pulled from the
# raw graph specifically because it's excluded from conflict classification.
# Only for علوم: history/geography lessons don't force hero<->pivot to be
# protection, so that edge is already a
# normal breakable edge in the filtered Plot there — pulling it here too
# would show it twice, once intact and once negated.
hero_pivot_edges = []
G = nx.read_graphml("../create&update/filtered_knowledge_graph.graphml")
if hero and pivot and G.graph.get("subject", "علوم") == "علوم":
    id_to_label = {n: G.nodes[n].get("label", n) for n in G.nodes()}
    label_to_id = {v: k for k, v in id_to_label.items()}
    if label_to_id.get(hero) is not None and label_to_id.get(pivot) is not None:
        hero_id, pivot_id = label_to_id[hero], label_to_id[pivot]
        for u, v in ((hero_id, pivot_id), (pivot_id, hero_id)):
            if G.has_edge(u, v):
                hero_pivot_edges.append({
                    "source": id_to_label[u],
                    "target": id_to_label[v],
                    "relation": G.edges[u, v].get("label", ""),
                })

# a node whose concept got negated (it has at least one broken outgoing
# edge) keeps that negated label everywhere it's displayed — the node list,
# and any OTHER edge from the same source (positional ones included) — so
# the same concept doesn't show under two different labels in one diagram.
for e in positional_edges:
    if e["source"] in negated_source_labels:
        e["source"] = negated_source_labels[e["source"]]

display_label = {label: negated_source_labels.get(
    label, label) for label in roles}

antonym_plot = {
    "nodes": [{"label": display_label[label], "role": role} for label, role in roles.items()],
    "intact_edges": hero_pivot_edges + positional_edges,
    "broken_edges": antonym_edges,
}

os.makedirs("./results", exist_ok=True)
with open("./results/antonym_plot.json", "w", encoding="utf-8") as f:
    json.dump(antonym_plot, f, ensure_ascii=False, indent=4)

print("=== Antonym Plot (built from sna_plot_graph_filtered.json) ===")
print(f"nodes: {list(display_label.values())}")
print("intact (never broken):")
for e in hero_pivot_edges:
    print(f"  {e['source']} --[{e['relation'].strip()}]--> {e['target']}")
for e in positional_edges:
    print(
        f"  {e['source']} --[{e['relation'].strip()}]--> {e['target']}  (positional, not breakable)")
print("broken (negated):")
for e in antonym_edges:
    print(f"  {e['source']} --[{e['relation']}]--> {e['target']}  (was: {e['original_relation'].strip()})")
print("\nsaved to results/antonym_plot.json")

# visualize — same role colors/sizes as the original Plot
node_color = {"البطل": "#FF4500", "المحور": "#90D5FF", "رئيسية": "#FFA500"}
node_size = {"البطل": 40, "المحور": 35, "رئيسية": 25}

net = Network(notebook=False, directed=True, height="750px", width="100%",
              cdn_resources="in_line")

for label, role in roles.items():
    shown = display_label[label]
    net.add_node(shown, label=shown, title=f"الدور: {role}",
                 color=node_color.get(role, "#D3D3D3"), size=node_size.get(role, 20))

for e in hero_pivot_edges:
    net.add_edge(display_label.get(e["source"], e["source"]),
                 display_label.get(e["target"], e["target"]), label=e["relation"].strip(),
                 color="#2ECC71", width=3, title="علاقة سليمة (لم تنكسر)",
                 font={"size": 10, "align": "horizontal"})

for e in positional_edges:
    net.add_edge(e["source"], display_label.get(e["target"], e["target"]),
                 label=e["relation"].strip(),
                 color="#2ECC71", width=2, title="علاقة موضعية (غير قابلة للنقض)",
                 font={"size": 10, "align": "horizontal"})

for e in antonym_edges:
    net.add_edge(e["source"], display_label.get(e["target"], e["target"]),
                 label=e["relation"].strip(),
                 color="#C0392B", width=3,
                 title=f"الأصل: {e['original_relation'].strip()}",
                 font={"size": 10, "align": "horizontal"})

net.toggle_physics(True)

with open("./results/antonym_plot.html", "w", encoding="utf-8") as f:
    f.write(net.generate_html())

print("saved to results/antonym_plot.html")
