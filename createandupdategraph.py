import json
import networkx as nx
from pyvis.network import Network
import requests
# import time


# with open('nlp/nlp_output.json', 'r', encoding='utf-8') as f:
with open('nlp/nlp2_output.json', 'r', encoding='utf-8') as f:
    # with open('nlp/nlp3_output.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

G = nx.DiGraph()

for node in data["nodes"]:
    G.add_node(node["id"], label=node["label"],
               title=node["type"], color="#97C2FC")

for edge in data["edges"]:
    G.add_edge(edge["source"], edge["target"],
               label=edge["type"], color="gray")

nx.write_graphml(G, "create&update/knowledge_graph.graphml")
print(" [الخرج 1]: تم حفظ ملف الشبكة البرمجي (knowledge_graph.graphml) بنجاح!")

print(" جاري توليد الصفحة التفاعلية للغراف بالعربية...")

net = Network(notebook=False, directed=True, height="750px",
              width="100%", cdn_resources='in_line')

net.from_nx(G)
net.toggle_physics(True)

html_content = net.generate_html()

with open("create&update/knowledge_graph.html", "w", encoding="utf-8") as out:
    out.write(html_content)

print(" تم حل مشكلة الترميز وحفظ ملف العرض بنجاح!")
print(" اذهبي الآن وافتحي الملف (knowledge_graph.html) في المتصفح وسيعمل فوراً وسترين الغراف بالعربي!")


# update graph

# headers = {
#     'User-Agent': 'KnowledgeGraphBot/1.0 (contact@example.com)'
# }

# for node_id in list(G.nodes):
#     node_label = G.nodes[node_id].get("label", "").strip()

#     if not node_label:
#         continue

#     target_title = node_label

#     wiki_params = {
#         "action": "query",
#         "format": "json",
#         "prop": "extracts",
#         "exintro": True,
#         "explaintext": True,
#         "titles": target_title,
#         "redirects": 1
#     }

#     try:
#         response = requests.get("https://ar.wikipedia.org/w/api.php", params=wiki_params, headers=headers).json()
#         pages = response.get("query", {}).get("pages", {})
#         page_data = next(iter(pages.values()))
#         extract_text = page_data.get("extract", "")

#         if not extract_text or "missing" in page_data:
#             search_params = {
#                 "action": "query",
#                 "format": "json",
#                 "list": "search",
#                 "srsearch": node_label,
#                 "srlimit": 1
#             }
#             search_response = requests.get("https://ar.wikipedia.org/w/api.php", params=search_params, headers=headers).json()
#             search_results = search_response.get("query", {}).get("search", [])

#             if search_results:
#                 target_title = search_results[0]["title"]
#                 wiki_params["titles"] = target_title
#                 response = requests.get("https://ar.wikipedia.org/w/api.php", params=wiki_params, headers=headers).json()
#                 pages = response.get("query", {}).get("pages", {})
#                 page_data = next(iter(pages.values()))
#                 extract_text = page_data.get("extract", "")

#         if extract_text:
#             full_intro_text = extract_text.strip()
#             final_definition = ""

#             if " هي " in full_intro_text:
#                 after_keyword = full_intro_text.split(" هي ", 1)[1]
#                 final_definition = after_keyword.split('.', 1)[0].strip() + "."

#             elif " هو " in full_intro_text:
#                 after_keyword = full_intro_text.split(" هو ", 1)[1]
#                 final_definition = after_keyword.split('.', 1)[0].strip() + "."

#             else:
#                 first_sentence = full_intro_text.split('.', 1)[0].strip()
#                 final_definition = first_sentence + "." if first_sentence else ""

#             words = final_definition.split()
#             formatted_label = ""
#             for i in range(0, len(words), 5):
#                 formatted_label += " ".join(words[i:i+5]) + "\n"

#             def_node_id = f"wiki_def_{node_id}"


with open('create&update/wiki_nodes.json', 'r', encoding='utf-8') as l:
    data = json.load(l)

K = nx.DiGraph()

for node in data["nodes"]:
    K.add_node(node["id"], label=node["label"],
               title=node["type"], color="blue")

for edge in data["edges"]:
    K.add_edge(edge["source"], edge["target"],
               label=edge["type"], color="green")


G_label_to_id = {
    attrs.get("label", "").strip(): node_id
    for node_id, attrs in G.nodes(data=True)
}

K_label_to_id = {
    attrs.get("label", "").strip(): node_id
    for node_id, attrs in K.nodes(data=True)
}

common_labels = set(G_label_to_id.keys()).intersection(
    set(K_label_to_id.keys()))

if not common_labels:
    print("No common nodes found between G and K, nothing merged.")
else:
    print(f"Common nodes found: {common_labels}")

    k_id_remap = {}
    for k_node_id, attrs in K.nodes(data=True):
        label = attrs.get("label", "").strip()
        if label in G_label_to_id:
            k_id_remap[k_node_id] = G_label_to_id[label]
        else:
            k_id_remap[k_node_id] = f"K_{k_node_id}"

    for k_node_id, attrs in K.nodes(data=True):
        g_node_id = k_id_remap[k_node_id]
        label = attrs.get("label", "").strip()

        if label in common_labels:
            pass
        else:
            G.add_node(g_node_id, **attrs)

    for src, tgt, edge_attrs in K.edges(data=True):
        g_src = k_id_remap[src]
        g_tgt = k_id_remap[tgt]
        G.add_edge(g_src, g_tgt, **edge_attrs)

        # if((G.nodes.get(def_node_id) is None)):
        #  K.add_node(
        #     def_node_id,
        #     label=formatted_label.strip(),
        #     title=f"نص مقتطع من ويكيبيديا لـ: {target_title}",
        #     color="#A8E6CF"
        #  )

        #  G.add_edge(node_id, def_node_id, label="تعريف", color="#2ECC71")
        # print(f"   '{node_label}' : '{formatted_label.strip()}'")
# else:
#             print(f" the following term is not found in wikipedia '{node_label}'")
#             except Exception as e:
# print(f"error: {str(e)}")


nx.write_graphml(G, "create&update/wiki_extracted_knowledge_graph.graphml")

wiki_net = Network(notebook=False, directed=True,
                   height="750px", width="100%", cdn_resources='in_line')
wiki_net.from_nx(G)
wiki_net.toggle_physics(True)
wiki_html_content = wiki_net.generate_html()

with open("create&update/wiki_extracted_knowledge_graph.html", "w", encoding="utf-8") as out:
    out.write(wiki_html_content)
