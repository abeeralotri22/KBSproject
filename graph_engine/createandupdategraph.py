import json
import networkx as nx
from pyvis.network import Network
import requests
# import time


# with open('nlp/nlp_output.json', 'r', encoding='utf-8') as f:  # علوم1 ✅
# with open('nlp/nlp2_output.json', 'r', encoding='utf-8') as f: # تنوع بيئي
# with open('nlp/nlp4_output.json', 'r', encoding='utf-8') as f:  # علوم2 
# with open('nlp/nlp5_output.json', 'r', encoding='utf-8') as f:  # علوم3 ✅
# with open('nlp/nlp6_output.json', 'r', encoding='utf-8') as f:  # علوم4 ✅ تسلسل
# with open('nlp/nlp_text1.json', 'r', encoding='utf-8') as f:  # test: الليف العضلي المخطط (descriptive) النص ركيك
# with open('nlp/nlp_text2.json', 'r', encoding='utf-8') as f:  # test: المشيمية (descriptive) قصير
# with open('nlp/nlp_text3.json', 'r', encoding='utf-8') as f:  # test: الشبكية (descriptive) تحوي
# with open('nlp/nlp_text4.json', 'r', encoding='utf-8') as f:  # test: دور الشبكية (descriptive) تحوي
# with open('nlp/nlp_text5.json', 'r', encoding='utf-8') as f:  # test: الإنارة (causal) ✅
# with open('nlp/nlp_text6.json', 'r', encoding='utf-8') as f:  # test: المريء (descriptive) النص ركيك
# with open('nlp/nlp_text7.json', 'r', encoding='utf-8') as f:  # test: تسوس الأسنان (causal ) ✅
# with open('nlp/nlp_text8.json', 'r', encoding='utf-8') as f:  # test: المعدة (descriptive) ✅ تسلسل
# with open('nlp/nlp_text9.json', 'r', encoding='utf-8') as f:  # test: التعب العضلي (causal ) ✅
# with open('nlp/nlp_text_eye_combined.json', 'r', encoding='utf-8') as f:  # test: العين مجمّعة (نصوص 2+3+4، descriptive)
# with open('nlp/nlp_text10.json', 'r', encoding='utf-8') as f:  # test: مسار السمع /  تسلسل ✅

# with open('nlp/new_nlp_text1.json', 'r', encoding='utf-8') as f:  # test: الحمل والولادة hub
# with open('nlp/new_nlp_text2.json', 'r', encoding='utf-8') as f:  # test: تجدد البشرة (causal )✅
# with open('nlp/new_nlp_text4.json', 'r', encoding='utf-8') as f:  # test: كمون العمل (causal )✅
# with open('nlp/new_nlp_text5.json', 'r', encoding='utf-8') as f:  # test: باحة فيرنكه (تسلسل) ✅
# with open('nlp/new_nlp_text6.json', 'r', encoding='utf-8') as f:  # test: المرونة العصبية والذاكرة (mixed)  (sus)
# with open('nlp/new_nlp_text7.json', 'r', encoding='utf-8') as f:  # test: عضلات الأذن الوسطى (causal, dual branch) ✅
# with open('nlp/new_nlp_text8.json', 'r', encoding='utf-8') as f:  # test: كمون المستقبل السمعي (causal ) ✅
# with open('nlp/new_nlp_text9.json', 'r', encoding='utf-8') as f:  # test: إنتاش حبة الطلع (descريptive/process) (sus) 

# with open('nlp/geo_text1.json', 'r', encoding='utf-8') as f:  # test: انتاج حيواني (hub)  sus
# with open('nlp/geo_text2.json', 'r', encoding='utf-8') as f:  # test: تملح التربة (hub) ✅
# with open('nlp/geo_text3.json', 'r', encoding='utf-8') as f:  # test: التربة الصحراوية والبادية السورية (hub)  ✅
# with open('nlp/geo_text4.json', 'r', encoding='utf-8') as f:  # test: مناخ الوطن العربي وعوامله (hub) ✅
# with open('nlp/geo_text5.json', 'r', encoding='utf-8') as f:  # test: مقومات السياحة في الوطن العربي (hub) ✅
# with open('nlp/geo_text6.json', 'r', encoding='utf-8') as f:  # test: مناخ سورية وفصوله ورياحه (hub) ✅
# with open('nlp/geo_text7.json', 'r', encoding='utf-8') as f:  # test: البادية السورية /  تسلسل ✅

# with open('nlp/hist_text1.json', 'r', encoding='utf-8') as f: # التاريخ sus
# with open('nlp/hist_text2.json', 'r', encoding='utf-8') as f:  # test: ثورة 1919 المصرية (hub) ✅
# with open('nlp/hist_text3.json', 'r', encoding='utf-8') as f:  # test: التنافس البريطاني الفرنسي على مصر (hub) ✅


with open('nlp/llm_output.json', 'r', encoding='utf-8') as f:


# with open('nlp/text1_output.json', 'r', encoding='utf-8') as f:
# with open('nlp/text2_output.json', 'r', encoding='utf-8') as f:
# with open('nlp/text3_output.json', 'r', encoding='utf-8') as f:
# with open('nlp/text4_output.json', 'r', encoding='utf-8') as f:
# with open('nlp/text5_output.json', 'r', encoding='utf-8') as f:
# with open('nlp/text6_output.json', 'r', encoding='utf-8') as f:
# with open('nlp/text7_output.json', 'r', encoding='utf-8') as f:
# with open('nlp/text8_output.json', 'r', encoding='utf-8') as f:
# with open('nlp/text9_output.json', 'r', encoding='utf-8') as f:


# with open('nlp/judy.json', 'r', encoding='utf-8') as f:
# with open('nlp/judy2.json', 'r', encoding='utf-8') as f: hub الشبكية ✅
# with open('nlp/judy3.json', 'r', encoding='utf-8') as f: # الليف العضلي ✅
# with open('nlp/judy4.json', 'r', encoding='utf-8') as f: # المشيمة
# with open('nlp/judy5.json', 'r', encoding='utf-8') as f:
# with open('nlp/judy6.json', 'r', encoding='utf-8') as f: الانارة
# with open('nlp/judy7.json', 'r', encoding='utf-8') as f: # تسوس
# with open('nlp/judy8.json', 'r', encoding='utf-8') as f:  # معدة ، علاقات غريبة
# with open('nlp/judy9.json', 'r', encoding='utf-8') as f:
# with open('nlp/llm_output.json', 'r', encoding='utf-8') as f:

    data = json.load(f)

G = nx.DiGraph()
if "subject" in data:
    G.graph["subject"] = data["subject"]

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
