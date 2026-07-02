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
important = set(crit["important_nodes"])

hero_id = label_to_id[hero]
pivot_id = label_to_id[pivot]

# only البطل، المحور، رئيسية , drop فرعية
important_roles = {"البطل", "المحور", "رئيسية"}
visible_nodes = {label for label,
                 role in roles.items() if role in important_roles}

# conflict detection
conflict_actors = [
    X for X in (important - {hero, pivot})
    if G.has_edge(label_to_id[X], pivot_id)
]

conflicts = []
for X in conflict_actors:
    X_id = label_to_id[X]
    reactors = [Y for Y in important if Y !=
                X and G.has_edge(label_to_id[Y], X_id)]

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
        "action_edge":    {
            "source": X, "target": pivot,
            "relation": G.edges[X_id, pivot_id].get("label", ""),
        },
        "reaction_edges": [
            {"source": Y, "target": X,
             "relation": G.edges[label_to_id[Y], X_id].get("label", "")}
            for Y in reactors
        ],
    })

action_edges = {(c["actor"], pivot) for c in conflicts}
reaction_edges = {(Y, c["actor"]) for c in conflicts for Y in c["reactors"]}

node_color = {"البطل": "#FF4500", "المحور": "#90D5FF", "رئيسية": "#FFA500"}
node_size = {"البطل": 40,        "المحور": 35,        "رئيسية": 25}


def edge_style(s, t):
    if (s, t) in action_edges:
        return {"color": "#E67E22", "width": 3, "type": "فعل"}
    if (s, t) in reaction_edges:
        return {"color": "#E74C3C", "width": 3, "type": "رد فعل"}
    return {"color": "#AAAAAA", "width": 1, "type": None}


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
print("saved to results/sna_plot_graph_filtered.html")
