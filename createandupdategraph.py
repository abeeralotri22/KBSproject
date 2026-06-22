import json
import networkx as nx
from pyvis.network import Network
import requests


with open('nlp_output.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

G = nx.DiGraph()

for node in data["nodes"]:
    G.add_node(node["id"], label=node["label"], title=node["type"], color="#97C2FC")

for edge in data["edges"]:
    G.add_edge(edge["source"], edge["target"], label=edge["type"], color="gray")

nx.write_graphml(G, "knowledge_graph.graphml")
print(" [الخرج 1]: تم حفظ ملف الشبكة البرمجي (knowledge_graph.graphml) بنجاح!")

print(" جاري توليد الصفحة التفاعلية للغراف بالعربية...")

net = Network(notebook=False, directed=True, height="750px", width="100%", cdn_resources='in_line')

net.from_nx(G)
net.toggle_physics(True)

html_content = net.generate_html()

with open("knowledge_graph.html", "w", encoding="utf-8") as out:
    out.write(html_content)

print(" تم حل مشكلة الترميز وحفظ ملف العرض بنجاح!")
print(" اذهبي الآن وافتحي الملف (knowledge_graph.html) في المتصفح وسيعمل فوراً وسترين الغراف بالعربي!")


# update graph

headers = {
    'User-Agent': 'KnowledgeGraphBot/1.0 (contact@example.com)'
}

for node_id in list(G.nodes):
    node_label = G.nodes[node_id].get("label", "").strip()
    
    if not node_label:
        continue
        
    target_title = node_label

    wiki_params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "titles": target_title,
        "redirects": 1
    }
    
    try:
        response = requests.get("https://ar.wikipedia.org/w/api.php", params=wiki_params, headers=headers).json()
        pages = response.get("query", {}).get("pages", {})
        page_data = next(iter(pages.values()))
        extract_text = page_data.get("extract", "")

        if not extract_text or "missing" in page_data:
            search_params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": node_label,
                "srlimit": 1
            }
            search_response = requests.get("https://ar.wikipedia.org/w/api.php", params=search_params, headers=headers).json()
            search_results = search_response.get("query", {}).get("search", [])
            
            if search_results:
                target_title = search_results[0]["title"]
                wiki_params["titles"] = target_title
                response = requests.get("https://ar.wikipedia.org/w/api.php", params=wiki_params, headers=headers).json()
                pages = response.get("query", {}).get("pages", {})
                page_data = next(iter(pages.values()))
                extract_text = page_data.get("extract", "")

        if extract_text:
            full_intro_text = extract_text.strip()
            final_definition = ""
            
            if " هي " in full_intro_text:
                after_keyword = full_intro_text.split(" هي ", 1)[1]
                final_definition = after_keyword.split('.', 1)[0].strip() + "."
                
            elif " هو " in full_intro_text:
                after_keyword = full_intro_text.split(" هو ", 1)[1]
                final_definition = after_keyword.split('.', 1)[0].strip() + "."
                
            else:
                first_sentence = full_intro_text.split('.', 1)[0].strip()
                final_definition = first_sentence + "." if first_sentence else ""

            words = final_definition.split()
            formatted_label = ""
            for i in range(0, len(words), 5):
                formatted_label += " ".join(words[i:i+5]) + "\n"

            def_node_id = f"wiki_def_{node_id}"
            G.add_node(
                def_node_id, 
                label=formatted_label.strip(), 
                title=f"نص مقتطع من ويكيبيديا لـ: {target_title}", 
                color="#A8E6CF"
            )
            
            G.add_edge(node_id, def_node_id, label="تعريف", color="#2ECC71")
            print(f"   the term is found in wikipedia")
        else:
            print(f" the following term is not found in wikipedia '{node_label}'")
            
    except Exception as e:
        print(f"error: {str(e)}")


nx.write_graphml(G, "wiki_extracted_knowledge_graph.graphml")

wiki_net = Network(notebook=False, directed=True, height="750px", width="100%", cdn_resources='in_line')
wiki_net.from_nx(G)
wiki_net.toggle_physics(True)
wiki_html_content = wiki_net.generate_html()

with open("wiki_extracted_knowledge_graph.html", "w", encoding="utf-8") as out:
    out.write(wiki_html_content)