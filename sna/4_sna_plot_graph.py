import networkx as nx
import json
from pyvis.network import Network

G = nx.read_graphml("../create&update/knowledge_graph.graphml")
id_to_label = {node: G.nodes[node].get("label", node) for node in G.nodes()}
label_to_id = {v: k for k, v in id_to_label.items()}

with open("./results/criticality_scores.json", "r", encoding="utf-8") as f:
    crit = json.load(f)

roles = crit["roles"]
hero = crit["hero"]
pivot = crit["pivot"]
main = set(crit["main"])

hero_id = label_to_id[hero]
pivot_id = label_to_id[pivot]

#  find conflict nodes
# X must be رئيسية AND (X → المحور) AND (البطل → X)
conflict_nodes = [
    X for X in main
    if G.has_edge(label_to_id[X], pivot_id) and G.has_edge(hero_id, label_to_id[X])
]

conflict_action = {(X, pivot) for X in conflict_nodes}  # فعل:    X → المحور
conflict_reaction = {(hero, X) for X in conflict_nodes}  # رد فعل: البطل → X

# style maps
node_color = {"البطل": "#FF4500", "المحور": "#90D5FF",
              "رئيسية": "#FFA500", "فرعية": "#D3D3D3"}
node_size = {"البطل": 40,        "المحور": 35,
             "رئيسية": 25,         "فرعية": 15}

edge_style = {
    "فعل":     {"color": "#E67E22", "width": 3},
    "رد فعل":  {"color": "#E74C3C", "width": 3},
    None:      {"color": "#AAAAAA", "width": 1},
}

#  build plot graph
P = nx.DiGraph()

for node_id in G.nodes():
    label = id_to_label[node_id]
    role = roles.get(label, "فرعية")
    P.add_node(label, role=role, color=node_color[role], size=node_size[role])

for src, tgt, data in G.edges(data=True):
    s = id_to_label[src]
    t = id_to_label[tgt]
    if (s, t) in conflict_action:
        etype = "فعل"
    elif (s, t) in conflict_reaction:
        etype = "رد فعل"
    else:
        etype = None
    P.add_edge(s, t, relation=data.get("label", ""), etype=etype,
               **edge_style[etype])

#  print summary
# print("=== أدوار العقد ===")
# for label, role in sorted(roles.items(), key=lambda x: ["البطل", "المحور", "رئيسية", "فرعية"].index(x[1])):
#     print(f"  [{role}] {label}")

# print(f"\n=== عقد الصراع ({len(conflict_nodes)}) ===")
# for X in conflict_nodes:
#     r1 = G.edges[label_to_id[X], pivot_id].get("label", "")
#     r2 = G.edges[hero_id, label_to_id[X]].get("label", "")
#     print(f"  {X} → {pivot}  ({r1})   [فعل]")
#     print(f"  {hero} → {X}  ({r2})   [رد فعل]")

#  save json
conflict_edges = [
    {"source": s, "target": t, "relation": d["relation"], "type": d["etype"]}
    for s, t, d in P.edges(data=True) if d["etype"]
]

plot_data = {
    "nodes": [{"label": n, "role": P.nodes[n]["role"]} for n in P.nodes()],
    "edges": [
        {"source": s, "target": t,
            "relation": d["relation"], "conflict_type": d["etype"]}
        for s, t, d in P.edges(data=True)
    ],
    "conflict_nodes":  conflict_nodes,
    "conflict_edges":  conflict_edges,
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
                 width=attrs["width"], font={"size": 10, "align": "middle"})

net.toggle_physics(True)

with open("./results/sna_plot_graph.html", "w", encoding="utf-8") as f:
    f.write(net.generate_html())

print("\n saved to sna_plot_graph.json && sna_plot_graph.html")
