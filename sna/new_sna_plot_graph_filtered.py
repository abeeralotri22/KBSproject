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

edges_by_type = {}
for e in edge_impact["edges_by_disruption"]:
    edges_by_type.setdefault(e["conflict_type"], set()).add(
        (e["source"], e["target"]))

loop_edges = edges_by_type.get("حلقة", set())
entry_edges = edges_by_type.get("دخول", set())
extension_edges = edges_by_type.get("امتداد", set())
hero_conflict_edges = edges_by_type.get("صراع_مع_البطل", set())
action_edges = edges_by_type.get("فعل", set())
all_conflict_edge_pairs = (loop_edges | entry_edges | extension_edges
                           | hero_conflict_edges | action_edges)

# only البطل، المحور، رئيسية are visible by role — plus any node that's an
# endpoint of a conflict/loop/entry/exit edge, even if its own role is فرعية
important_roles = {"البطل", "المحور", "رئيسية"}
visible_nodes = {label for label,
                 role in roles.items() if role in important_roles}
for s, t in all_conflict_edge_pairs:
    visible_nodes.add(s)
    visible_nodes.add(t)


def edge_style(s, t):
    if (s, t) in hero_conflict_edges:
        return {"color": "#E74C3C", "width": 3, "type": "صراع_مع_البطل"}
    if (s, t) in loop_edges:
        return {"color": "#9B59B6", "width": 3, "type": "حلقة"}
    if (s, t) in entry_edges:
        return {"color": "#3498DB", "width": 3, "type": "دخول"}
    if (s, t) in extension_edges:
        return {"color": "#1ABC9C", "width": 3, "type": "امتداد"}
    if (s, t) in action_edges:
        return {"color": "#E67E22", "width": 2, "type": "فعل"}
    return {"color": "#AAAAAA", "width": 1, "type": None}


node_color = {"البطل": "#FF4500", "المحور": "#90D5FF",
              "رئيسية": "#FFA500", "فرعية": "#D3D3D3"}
node_size = {"البطل": 40,        "المحور": 35,
             "رئيسية": 25,         "فرعية": 15}

# build filtered plot graph , only visible nodes and edges between them
P = nx.DiGraph()

for label in visible_nodes:
    role = roles[label]
    P.add_node(label, role=role, color=node_color[role], size=node_size[role])

for src, tgt, data in G.edges(data=True):
    s = id_to_label[src]
    t = id_to_label[tgt]
    if s in visible_nodes and t in visible_nodes:
        st = edge_style(s, t)
        if st["type"] is None:
            continue  # skip non-conflict edges
        P.add_edge(s, t, relation=data.get("label", ""), **st)

# save json
plot_data = {
    "nodes": [{"label": n, "role": P.nodes[n]["role"]} for n in P.nodes()],
    "edges": [
        {"source": s, "target": t,
            "relation": d["relation"], "conflict_type": d["type"]}
        for s, t, d in P.edges(data=True)
    ],
    "conflict_edges": [
        {"source": s, "target": t,
            "relation": d["relation"], "conflict_type": d["type"]}
        for s, t, d in P.edges(data=True) if d["type"]
    ],
}

with open("./results/sna_plot_graph_filtered.json", "w", encoding="utf-8") as f:
    json.dump(plot_data, f, ensure_ascii=False, indent=4)

# visualize
net = Network(notebook=False, directed=True, height="750px", width="100%",
              cdn_resources="in_line")

for node, attrs in P.nodes(data=True):
    net.add_node(node, label=node, title=f"الدور: {attrs['role']}",
                 color=attrs["color"], size=attrs["size"])

for s, t, attrs in P.edges(data=True):
    net.add_edge(s, t, label=attrs["relation"], color=attrs["color"],
                 width=attrs["width"], font={"size": 10, "align": "middle"})

net.toggle_physics(True)

with open("./results/sna_plot_graph_filtered.html", "w", encoding="utf-8") as f:
    f.write(net.generate_html())

print(f"visible nodes: {len(P.nodes())}  edges: {len(P.edges())}")
print("saved to results/sna_plot_graph_filtered.html && results/sna_plot_graph_filtered.json")
