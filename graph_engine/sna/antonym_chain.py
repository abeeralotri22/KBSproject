import networkx as nx
import json
import os
from pyvis.network import Network
from antonym_lexicon import negate_relation, negate_by_type, EVENT_TYPES, STATE_TYPES


with open("./results/criticality_scores.json", "r", encoding="utf-8") as f:
    crit = json.load(f)

archetype = crit.get("archetype")
chain_subtype = crit.get("chain_subtype")

if archetype != "chain" or chain_subtype != "causal":
    raise SystemExit(
        f"antonym_chain.py only applies to causal chains — this graph is "
        f"archetype={archetype!r} subtype={chain_subtype!r}"
    )

with open("./results/sna_plot_graph_filtered.json", "r", encoding="utf-8") as f:
    plot = json.load(f)

roles = {n["label"]: n["role"] for n in plot["nodes"]}
# a graph can have SEVERAL independent triggers
trigger_labels = [label for label, role in roles.items() if role == "المحفز"]

# node-type-aware concept negation (عدم/عدم وجود)
raw = nx.read_graphml("../create&update/filtered_knowledge_graph.graphml")
label_to_type = {d.get("label", "").strip(): d.get("title", "").strip()
                 for _, d in raw.nodes(data=True)}

# build the Plot as its own graph
P = nx.DiGraph()
for n in plot["nodes"]:
    P.add_node(n["label"], role=n["role"])
for e in plot["edges"]:
    P.add_edge(e["source"], e["target"], relation=e["relation"])

negated_triggers = {}
affected_labels = set()
for trigger_label in trigger_labels:
    negated_triggers[trigger_label] = negate_by_type(
        trigger_label, label_to_type.get(trigger_label.strip(), ""))
    affected_labels |= set(nx.descendants(P, trigger_label))

prevented_edges = []
positional_edges = []
for u, v, d in P.edges(data=True):
    if u in negated_triggers:
        source_label = negated_triggers[u]
    elif u in affected_labels:
        source_label = u
    else:
        continue
    original_relation = d["relation"]
    negated_relation = negate_relation(original_relation)
    entry = {
        "source": source_label,
        "target": v,
        "original_relation": original_relation,
        "relation": negated_relation,
        "reason": "لم يحدث لأن السبب الأصلي لم يقع",
    }
    if negated_relation.strip() == original_relation.strip():
        positional_edges.append(entry)
    else:
        prevented_edges.append(entry)

antonym_chain = {
    "triggers": trigger_labels,
    "negated_triggers": negated_triggers,
    "prevented_nodes": sorted(affected_labels),
    "prevented_edges": prevented_edges,
    "positional_edges": positional_edges,
}

os.makedirs("./results", exist_ok=True)
with open("./results/antonym_chain.json", "w", encoding="utf-8") as f:
    json.dump(antonym_chain, f, ensure_ascii=False, indent=4)

print("=== Antonym Chain (built from sna_plot_graph_filtered.json) ===")
for trigger_label in trigger_labels:
    print(
        f"trigger: {trigger_label}  ->  negated: {negated_triggers[trigger_label]}")
print(f"affected (never occur): {sorted(affected_labels)}")
for e in prevented_edges:
    print(f"  {e['source']} --[{e['relation']}]--> {e['target']}  "
          f"(was: {e['original_relation'].strip()})")
for e in positional_edges:
    print(
        f"  {e['source']} --[{e['relation']}]--> {e['target']}  (positional, not breakable)")

# visualize
node_color = {"المحفز": "#FF4500", "النتيجة": "#90D5FF", "مرحلة": "#FFA500",
              "حل": "#2ECC71", "أثر_جانبي": "#D3D3D3"}
node_size = {"المحفز": 40, "النتيجة": 35,
             "مرحلة": 25, "حل": 25, "أثر_جانبي": 15}

net = Network(notebook=False, directed=True, height="750px", width="100%",
              cdn_resources="in_line")

for trigger_label in trigger_labels:
    node_type = label_to_type.get(trigger_label.strip(), "")
    if node_type in EVENT_TYPES:
        title = "المحفز (منقوض)"
    elif node_type in STATE_TYPES:
        title = "المحفز (نُفي وجوده)"
    else:
        title = "المحفز (كيان ثابت، لم يُنقض)"
    net.add_node(negated_triggers[trigger_label], label=negated_triggers[trigger_label],
                 title=title, color=node_color["المحفز"], size=node_size["المحفز"])

untouched_labels = set(P.nodes()) - affected_labels - set(trigger_labels)
for label in affected_labels | untouched_labels:
    role = roles.get(label, "أثر_جانبي")
    tag = " (لم يحدث)" if label in affected_labels else ""
    net.add_node(label, label=label, title=f"الدور: {role}{tag}",
                 color=node_color.get(role, "#D3D3D3"), size=node_size.get(role, 15))

for e in prevented_edges:
    net.add_edge(e["source"], e["target"], label=e["relation"],
                 color="#AAAAAA", width=2, dashes=True,
                 title=f"الأصل: {e['original_relation'].strip()} — {e['reason']}",
                 font={"size": 10, "align": "horizontal"})

for e in positional_edges:
    net.add_edge(e["source"], e["target"], label=e["relation"].strip(),
                 color="#2ECC71", width=2, title="علاقة موضعية (غير قابلة للنقض)",
                 font={"size": 10, "align": "horizontal"})

for u, v, d in P.edges(data=True):
    if u in untouched_labels and v in untouched_labels:
        net.add_edge(u, v, label=d["relation"].strip(), color="#E67E22", width=2,
                     font={"size": 10, "align": "horizontal"})

net.toggle_physics(True)

with open("./results/antonym_chain.html", "w", encoding="utf-8") as f:
    f.write(net.generate_html())

print("\nsaved to results/antonym_chain.json && results/antonym_chain.html")
