import networkx as nx
import json
from pyvis.network import Network

G = nx.read_graphml("../create&update/filtered_knowledge_graph.graphml")
id_to_label = {node: G.nodes[node].get("label", node) for node in G.nodes()}
label_to_id = {v: k for k, v in id_to_label.items()}

with open("./results/criticality_scores.json", "r", encoding="utf-8") as f:
    crit = json.load(f)

roles = crit["roles"]
hero = crit["hero"]
pivot = crit["pivot"]

with open("./results/edge_impact_summary.json", "r", encoding="utf-8") as f:
    edge_impact = json.load(f)

conflicts = [c for c in edge_impact["conflicts"] if "type" in c]
cycles = [c for c in edge_impact["conflicts"] if "cycles" in c]

# build sets for fast edge lookup, one per conflict_type produced by new_sna_edge_impact2.py
edges_by_type = {}
for e in edge_impact["edges_by_disruption"]:
    edges_by_type.setdefault(e["conflict_type"], set()).add(
        (e["source"], e["target"]))

loop_edges = edges_by_type.get("حلقة", set())
entry_edges = edges_by_type.get("دخول", set())
extension_edges = edges_by_type.get("امتداد", set())
hero_conflict_edges = edges_by_type.get("صراع_مع_البطل", set())
action_edges = edges_by_type.get("فعل", set())
causal_edges = edges_by_type.get("مسار_سببي", set())
sequence_edges = edges_by_type.get("تسلسل", set())
resolution_edges = edges_by_type.get("حل", set())
addition_edges = edges_by_type.get("إضافة", set())


# three distinct palettes  hub/causal-chain/sequence-chain
node_color = {
    "البطل": "#FF4500", "المحور": "#90D5FF", "رئيسية": "#FFA500", "فرعية": "#D3D3D3",
    "المحفز": "#FF8000", "النتيجة": "#4DB3F3", "مرحلة": "#FEBC66",
    "حل": "#2ECC71", "أثر_جانبي": "#D3D3D3",
    "البداية": "#B9FE88", "الخاتمة": "#4DB3F3", "خطوة": "#FFFD93", "فرعي": "#D3D3D3",
}
node_size = {
    "البطل": 40, "المحور": 35, "رئيسية": 25, "فرعية": 15,
    "المحفز": 35, "النتيجة": 30, "مرحلة": 20,
    "حل": 20, "أثر_جانبي": 12,
    "البداية": 35, "الخاتمة": 30, "خطوة": 20, "فرعي": 12,
}


def edge_style(s, t):
    if (s, t) in hero_conflict_edges:
        return {"color": "#E74C3C", "width": 3, "type": "صراع_مع_البطل"}
    if (s, t) in loop_edges:
        return {"color": "#9B59B6", "width": 3, "type": "حلقة"}
    if (s, t) in entry_edges:
        return {"color": "#3498DB", "width": 3, "type": "دخول"}
    if (s, t) in extension_edges:
        return {"color": "#1ABC9C", "width": 3, "type": "خروج"}
    if (s, t) in action_edges:
        return {"color": "#E67E22", "width": 2, "type": "فعل"}
    if (s, t) in causal_edges:
        return {"color": "#E67E22", "width": 3, "type": "مسار_سببي"}
    if (s, t) in sequence_edges:
        return {"color": "#3498DB", "width": 2, "type": "تسلسل"}
    if (s, t) in resolution_edges:
        return {"color": "#2ECC71", "width": 3, "type": "حل"}
    if (s, t) in addition_edges:
        return {"color": "#1ABC9C", "width": 2, "type": "إضافة"}
    return {"color": "#AAAAAA", "width": 1, "type": None}


#  build plot graph
P = nx.DiGraph()

for node_id in G.nodes():
    label = id_to_label[node_id]
    role = roles.get(label, "فرعية")
    P.add_node(label, role=role, color=node_color[role], size=node_size[role])

for src, tgt, data in G.edges(data=True):
    s = id_to_label[src]
    t = id_to_label[tgt]
    st = edge_style(s, t)
    P.add_edge(s, t, relation=data.get("label", ""), **st)


# save  json
all_conflict_edges = [
    {"source": s, "target": t,
        "relation": d["relation"], "conflict_type": d["type"]}
    for s, t, d in P.edges(data=True) if d["type"]
]

plot_data = {
    "nodes": [{"label": n, "role": P.nodes[n]["role"]} for n in P.nodes()],
    "edges": [
        {"source": s, "target": t,
            "relation": d["relation"], "conflict_type": d["type"]}
        for s, t, d in P.edges(data=True)
    ],
    "conflicts":       conflicts,
    "cycles":          cycles,
    "conflict_edges":  all_conflict_edges,
}

with open("./results/sna_plot_graph.json", "w", encoding="utf-8") as f:
    json.dump(plot_data, f, ensure_ascii=False, indent=4)

#  visualize
net = Network(notebook=False, directed=True, height="750px", width="100%",
              cdn_resources="in_line")

for node, attrs in P.nodes(data=True):
    net.add_node(node, label=node, title=f"الدور: {attrs['role']}",
                 color=attrs["color"], size=attrs["size"])

for s, t, attrs in P.edges(data=True):
    net.add_edge(s, t, label=attrs["relation"], color=attrs["color"],
                 width=attrs["width"], font={"size": 10, "align": "horizontal"})

net.toggle_physics(True)

with open("./results/sna_plot_graph.html", "w", encoding="utf-8") as f:
    f.write(net.generate_html())

print("\n saved to sna_plot_graph.json && sna_plot_graph.html")
