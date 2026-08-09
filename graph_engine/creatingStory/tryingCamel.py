import json
import random
import networkx as nx
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer
from camel_tools.morphology.generator import Generator
from camel_tools.tokenizers.word import simple_word_tokenize


db_analysis = MorphologyDB.builtin_db(flags='a')
db_generation = MorphologyDB.builtin_db(flags='g')
analyzer = Analyzer(db_analysis)
generator = Generator(db_generation)

STORY_LEXICON = {
    "intros": [
        "كان يا ما كان، في قديم الزمان، وسالف العصر والأوان حتى كان.",
        "يُحكى في غابر الأزمان، وتتناقل الروايات عبر الأجيال أنهُ في سالف العهد،",
        "في أزمان بعيدة تملؤها الأسرار والعجائب، وقبل أن يطوي التاريخ صفحاته،"
    ],
    "disasters": [
        "حل دمار كبير بعد أن تآمرت قوى الشر على هذه المملكة الطيبة.",
        "عصفت بالمملكة رياح الفتنة والاضطراب بعد أن حرك الأشرار مكائدهم في الخفاء.",
        "انقلب أمن المملكة إلى خوف، واستحال سلامها صراعًا مريرًا بسبب مكائد خبيثة تدبر بليل."
    ],
    "discord_actions": [
        "فزرعت الفتنة بين {axis} و {rival}، ومن هنا بدأت المشاكل بالتصاعد..",
        "فحُكت المؤامرات لإيقاع الخلاف الشديد بين {axis} و {rival}، لتشتعل شرارة النزاع..",
        "فوسوس الأشرار بالسوء لتبدأ جدران الثقة بالانهيار بين {axis} و {rival}، لتنقسم القلوب.."
    ],
    "division_descriptions": [
        "انقسمت المملكة إلى قسمين متضادين يتنافسان على الدوام ويدمران أراضيهما للحصول على الحكم.",
        "وتشظت المملكة الطيبة إلى جبهتين متصارعتين، يسعى كل طرف لفرض سيطرته وإن كلف ذلك هلاك الرعية.",
        "وغدت المملكة مسرحًا لانقسام حاد وصراع داخلي مرير، يلتهم الأخضر واليابس طمعًا في بسط النفوذ."
    ],
    "night_descriptions": [
        "وفي ليلة عاصفة اشتد النزاع بين الطرفين،",
        "ومع مرور الأيام وفي ليلة مظلمة بلغت القلوب الحناجر من شدة النزاع،",
        "وحين وصلت الأزمة إلى ذروتها في ليلة ليلكاء لا ضياء فيها،"
    ],
    "hero_realization": [
        "أدرك أن ما حدث فيها ما هو إلا فتنة قام الأشرار بالتدبير لها للحصول على الحكم الحقيقي والسيطرة على المملكة.",
        "تيقن بفراسته أن هذا الشقاق ليس إلا فخًا نصبه الطامعون لتمزيق شمل المملكة وإخضاعها لنفوهم.",
        "فهم في الحال أن يد الغدر هي من حركت خيوط هذه اللعبة الدنيئة لتجريد المملكة من أمنها واستقرارها."
    ],
    "neglect_disasters": [
        "و ظنّت {actors} أنه لا بأس بترك {axis} وحيدة تصارع الأيام بمفردها، فتنكّرت لها و قطعت كل ما يصلها بها.",
        "و لم يخطر ببال {actors} أن الاستغناء عن {axis} سيجلب الشقاء على الجميع، فأدارت لها ظهرها دون تردد.",
        "و في غفلة من الزمن، توهّمت {actors} أن غيابها عن {axis} أمر هيّن، فقطعت أواصر الوصل و بينهم."
    ],
    "neglect_consequences": [
        "فأضحت {axis} تجرّ أذيال الوحدة، تتوجّع في صمت و لا يدري أحد بسوء حالها.",
        "فغرقت {axis} في بحر من الإهمال، تئنّ من وطأة الوحدة و لا مغيث و لا نصير.",
        "فذاقت {axis} مرارة الخذلان، و باتت تواجه مصيرها المجهول وحيدة بلا عون."
    ],
    "revenge_intros": [
        "لكن لم يكن ليمرّ هذا الجفاء دون أن يعلم به {hero}، الذي أقسم أن يقتصّ لـ{axis} ممن ظلمها.",
        "غير أن خبر هذا التنكّر بلغ مسامع {hero}، فآلى على نفسه ألا يدع الظلم يمرّ دون عقاب.",
        "و ما إن وصلت أنباء هذا الإهمال إلى {hero}، حتى عقد العزم أن ينتقم لـ{axis} في صمت و خفاء."
    ],
    "suffering_intros": [
        "و لم يمضِ وقت طويل حتى ذاق {actors} طعم العزلة التي طالما فرضوها على {axis}، فحاولوا استرضاء {hero}.",
        "فما هي إلا أيام حتى شعر {actors} بوطأة الوحدة التي عرفتها {axis} من قبلهم، فقصدوا {hero} طلبًا للصفح.",
        "و سرعان ما أدرك {actors} حجم الخسارة التي حلّت بهم، فسارعوا إلى {hero} يلتمسون العفو."
    ],
    "apology_demand": [
        "لكن {hero} رفض أن يقبل اعتذارهم، و طالبهم أولًا بأن يعتذروا لـ{axis} التي طالما تجاهلوها.",
        "غير أن {hero} أبى أن يسمع اعتذارهم قبل أن يذهبوا إلى {axis} و يطلبوا العفو منها أولًا.",
        "لكن {hero} لم يقبل صفحًا قبل أن يقفوا أمام {axis} معتذرين عمّا اقترفوه بحقها."
    ],
    "reconciliation_closings": [
        "و عاش الجميع في {place} في وئام و سلام، لا يعكر صفوهم خلاف أبدًا.",
        "و سادت المحبة من جديد بين أهل {place}، و طويت صفحة الجفاء إلى الأبد.",
        "و عمّ الوئام أرجاء {place}، فعاد الجميع أسرة واحدة متآلفة كما كانوا."
    ],
    "flaw_intros": [
        "و على الرغم من ذلك، كانت {axis} ذات صفات سيئة، إذ {describe_verb} الكثير من المواطنين مثل {witnesses} بالتعجرف و الكِبر،",
        "غير أن {axis} لم تخل من عيب فادح، إذ {describe_verb} الكثير من المواطنين مثل {witnesses} بالتعجرف و الكِبر،",
        "بيد أن سوءًا خفيًا كان يسكن {axis}، حتى {describe_verb} الكثير من المواطنين مثل {witnesses} بالتعجرف و الكِبر،",
    ],
    "false_confidence_lines": [
        "{believe_verb} {axis} بأن{axis_pron} {able_verb} الصمود بدون {hero}.. لكن سرعان ما تدهور وضع المملكة شيئًا فشيئًا.",
        "{believe_verb} {axis} في غرور{axis_pron} بأن{axis_pron} {able_verb} الاستغناء عن {hero}.. غير أن الأمور ما لبثت أن ساءت شيئًا فشيئًا.",
    ],
    "deficiency_intros" : [
        "ف{become_verb} {axis} تعاني، إذ {body}.",
        "و لم تمضِ أيام حتى {become_verb} {axis} تجرّ أذيال الوحدة، إذ {body}.",
    ],
    "hero_return_intros" : [
        "و فجأة {appear_verb} {hero} مجددًا في {place}، بعد سماع{hero_pron} الأخبار السيئة عن تدهور وضع {axis}{others}.",
        "و ما إن بلغت الأخبار السيئة عن تدهور وضع {axis}{others} مسامع {hero}، حتى {appear_verb} مجددًا في {place}.",
    ],
    "apology_open_lines" : [
        "{seize_verb} {axis} الفرصة و {initiate_verb} بالاعتذار{advice}..",
        "و لم تُضِع {axis} الفرصة، ف{initiate_verb} بالاعتذار{advice}..",
    ]
}


def analyze_arabic_word(word):
    tokens = simple_word_tokenize(word)
    if not tokens:
        return {}
    analyses = analyzer.analyze(tokens[0])
    if analyses:
        return analyses[0] 
    return {}

def is_feminine_nlp(label):
    analysis = analyze_arabic_word(label)
    if analysis and 'gen' in analysis:
        return analysis['gen'] == 'f'
    last_word = label.strip().split()[-1]
    return last_word.endswith("ة") or last_word.endswith("ت")

_ASPECT_CODES = {'perf': 'p', 'imperf': 'i', 'imper': 'c'}

def conjugate_verb_nlp(lemma, feminine, aspect='perf'):
    features = {
        'pos': 'verb', 'lex': lemma, 'asp': _ASPECT_CODES.get(aspect, aspect),
        'gen': 'f' if feminine else 'm', 'num': 's', 'per': '3'
    }
    generated_forms = generator.generate(lemma, features)
    if generated_forms:
        return generated_forms[0]['diac']
    return lemma + ("ت" if aspect == 'perf' and feminine else "")

def relation_is_comparative(relation):
    return relation.strip() in ("مثل", "نوع من")

def conjugate_relation_nlp(relation, feminine):
    if relation_is_comparative(relation):
        return relation.strip()
    words = relation.split()
    if words:
        base_verb = words[0]
        words[0] = conjugate_verb_nlp(base_verb, feminine, aspect='imperf')
    return " ".join(words)

def pron(feminine):
    return "ها" if feminine else "ه"

def fem_adj(masc_adj, feminine):
    return masc_adj + "ة" if feminine else masc_adj

def definite(phrase):
    return " ".join(w if w.startswith("ال") else f"ال{w}" for w in phrase.split())

def indefinite(phrase):
    words = []
    for w in phrase.split():
        if w.startswith("ال") and len(w) > 2:
            words.append(w[2:])
        else:
            words.append(w)
    return " ".join(words)

def load_story_data(path="./results/story_graph_data.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

STORY_DATA = load_story_data(r"C:\Users\Lenovo\OneDrive\Desktop\desktop\KBSproject\sna\results\story_graph_data.json")
roles = STORY_DATA["roles"]
graph_data = STORY_DATA["graph_data"]
conflicts = STORY_DATA.get("conflicts", [])

def build_domain_graph(data):
    G = nx.DiGraph()
    id_to_label = {n["id"]: n["label"] for n in data["nodes"]}
    for n in data["nodes"]:
        G.add_node(n["label"], type=n["type"])
    for e in data["edges"]:
        G.add_edge(id_to_label[e["source"]], id_to_label[e["target"]], relation=e["type"])
    return G

G_domain = build_domain_graph(graph_data)
HERO = roles["الشخصيات"]["البطل"]
AXIS = roles["الشخصيات"]["المحور"]
MAIN_CHARS = roles["الشخصيات"]["رئيسية"]
MINOR_CHARS = roles["الشخصيات"].get("فرعية", [])

AXIS_FEM = is_feminine_nlp(AXIS)
HERO_FEM = is_feminine_nlp(HERO)

def analyze_node_removal(G, node):
    lost_edges = []
    for u, v, data in G.edges(data=True):
        if u == node or v == node:
            lost_edges.append({"source": u, "target": v, "relation": data["relation"]})
    out_degree = G.out_degree(node)
    G_before_und = G.to_undirected()
    components_before = nx.number_connected_components(G_before_und)
    G_after = G.copy()
    G_after.remove_node(node)
    G_after_und = G_after.to_undirected()
    components_after = nx.number_connected_components(G_after_und) if G_after.number_of_nodes() else 0
    isolated_nodes = []
    if G_after.number_of_nodes():
        comps = list(nx.connected_components(G_after_und))
        main_comp = max(comps, key=len)
        for comp in comps:
            if comp is not main_comp:
                isolated_nodes.extend(sorted(comp))
    def reachability_sum(graph):
        return sum(len(nx.descendants(graph, n)) for n in graph.nodes)
    reachability_before = reachability_sum(G)
    reachability_after = reachability_sum(G_after)
    disruption_score = round(components_after / components_before, 2) if components_before else components_after
    return {
        "removed_node": node,
        "disruption_score": disruption_score,
        "agency_score": out_degree,
        "lost_edges_count": len(lost_edges),
        "lost_edges": lost_edges,
        "isolated_nodes": isolated_nodes,
        "components_before": components_before,
        "components_after": components_after,
        "graph_fragmented": components_after > components_before,
        "reachability_before": reachability_before,
        "reachability_after": reachability_after,
        "reachability_loss": reachability_before - reachability_after,
    }

impact = analyze_node_removal(G_domain, HERO) if HERO in G_domain else None

def group_lost_edges_by_relation(lost_edges):
    groups = {}
    for e in lost_edges:
        groups.setdefault(e["relation"], []).append(e["target"])
    return groups

def find_unused_edges(G, impact):
    if not impact: return list(G.edges(data=True))
    hero_edge_keys = {(e["source"], e["target"], e["relation"]) for e in impact["lost_edges"]}
    unused = []
    for u, v, d in G.edges(data=True):
        relation = d["relation"]
        if (u, v, relation) in hero_edge_keys: continue
        if relation in ("نوع من", "تتعاون") and (u == AXIS or v == AXIS): continue
        unused.append((u, v, relation))
    return unused

def build_witness_pool(G, impact):
    unused_edges = find_unused_edges(G, impact)
    order = []
    by_source = {}
    for u, v, relation in unused_edges:
        if u in (AXIS, HERO): continue
        if u not in by_source: order.append(u)
        by_source.setdefault(u, []).append((relation, v))
    return order, by_source

def render_witness_group(nodes, by_source):
    descriptions = []
    i = 0
    while i < len(nodes):
        node = nodes[i]
        node_fem = is_feminine_nlp(node) 
        rel_pronoun = "التي" if node_fem else "الذي"
        node_relations = [r for r, _ in by_source.get(node, [])]
        needs_pronoun = not (node_relations and all(relation_is_comparative(r) for r in node_relations))

        clauses = []
        for relation, target in by_source.get(node, []):
            verb = conjugate_relation_nlp(relation, node_fem) 
            clauses.append(verb if target.strip() in relation else f"{verb} {target}")

        text = f"{node.strip()} {rel_pronoun} " + " و ".join(clauses) if needs_pronoun else f"{node.strip()} " + " و ".join(clauses)

        if i + 1 < len(nodes):
            next_node = nodes[i + 1]
            targets_of_current = [t for _, t in by_source.get(node, [])]
            if next_node in targets_of_current:
                next_fem = is_feminine_nlp(next_node) 
                next_relations = [r for r, _ in by_source.get(next_node, [])]
                next_needs_pronoun = not (next_relations and all(relation_is_comparative(r) for r in next_relations))
                next_pronoun = "التي" if next_fem else "الذي"
                next_clauses = []
                for relation, target in by_source.get(next_node, []):
                    verb = conjugate_relation_nlp(relation, next_fem) 
                    next_clauses.append(verb if target.strip() in relation else f"{verb} {target}")
                if next_needs_pronoun:
                    text += f" و {next_pronoun} بدور{pron(next_fem)} " + " و ".join(next_clauses)
                else:
                    text += " و " + " و ".join(next_clauses)
                descriptions.append(text)
                i += 2
                continue
        descriptions.append(text)
        i += 1
    return descriptions

def render_deficiency_clauses(lost_edges):
    groups = group_lost_edges_by_relation(lost_edges)
    clauses = []
    for relation, targets in groups.items():
        if targets == [AXIS]:
            phrase = f"{relation}{pron(AXIS_FEM)}"
        else:
            phrase = f"{relation} " + " أو ".join(targets)
        clauses.append(phrase)
    return clauses

def render_restoration_clauses(lost_edges):
    groups = group_lost_edges_by_relation(lost_edges)
    clauses = []
    for relation, targets in groups.items():
        verb = conjugate_relation_nlp(relation, HERO_FEM) 
        if targets == [AXIS]:
            phrase = f"{verb}{pron(AXIS_FEM)}"
        else:
            phrase = f"{verb} " + " و ".join(targets)
        clauses.append(phrase)
    return clauses

def find_kind_relation(G, node, relation="نوع من"):
    for u, v, d in G.edges(data=True):
        if d["relation"] == relation and (u == node or v == node):
            return u if v == node else v
    return None

def find_relation_targets(G, node, relation):
    targets = []
    for u, v, d in G.edges(data=True):
        if d["relation"] == relation:
            if u == node: targets.append(v)
            elif v == node: targets.append(u)
    return targets


def gen_intro(G, roles):
    place = roles["المكان"]
    place_str = "مملكة البيولوجيا" if place == "غير محدد" else f"مملكة {place}"
    kind = find_kind_relation(G, AXIS, "نوع من")
    know_verb = conjugate_verb_nlp("عرف", AXIS_FEM, aspect='perf') 
    kind_phrase = f"{know_verb} هذه {AXIS} بكون{pron(AXIS_FEM)} نوعًا من {kind}" if kind else ""
    cooperators = find_relation_targets(G, AXIS, "تتعاون")
    coop_verb = conjugate_verb_nlp("تعاون", AXIS_FEM, aspect='imperf') 
    coop_phrase = f" و أن{pron(AXIS_FEM)} {coop_verb} مع {' و '.join(cooperators)}" if cooperators else ""
    role_phrase = f" و أن دور{pron(AXIS_FEM)} مهم و أساسي في مملكتنا" if (kind_phrase or coop_phrase) else f"كان دور{pron(AXIS_FEM)} أساسيًا و مهمًا"
    
    return f"{random.choice(STORY_LEXICON['intros'])} و في {place_str}، كان هناك {indefinite(AXIS)}. {kind_phrase}{coop_phrase}{role_phrase}."

def gen_negative_traits(pool, by_source):
    take = pool[:2]
    remaining = pool[2:]
    descriptions = render_witness_group(take, by_source)
    witnesses_str = " و ".join(descriptions) if descriptions else "بعض المواطنين"
    describe_verb = conjugate_verb_nlp("وصف", AXIS_FEM, aspect='perf') + pron(AXIS_FEM)
    hero_leave_verb = conjugate_verb_nlp("هجر", HERO_FEM, aspect='perf') + pron(AXIS_FEM)
    hero_abandon_verb = conjugate_verb_nlp("تخلى", HERO_FEM, aspect='perf')
    
    flaw_pattern = random.choice(STORY_LEXICON["flaw_intros"]).format(axis=AXIS.strip(), describe_verb=describe_verb, witnesses=witnesses_str)
    text = f"{flaw_pattern} هذا ما جعل {definite(HERO)} {hero_leave_verb} و {hero_abandon_verb} عن دور{pron(HERO_FEM)} في المملكة."
    return text, remaining

def gen_false_confidence():
    believe_verb = conjugate_verb_nlp("اعتقد", AXIS_FEM, aspect='perf')
    able_verb = conjugate_verb_nlp("استطاع", AXIS_FEM, aspect='imperf')
    return random.choice(STORY_LEXICON["false_confidence_lines"]).format(
        believe_verb=believe_verb, axis=AXIS.strip(), axis_pron=pron(AXIS_FEM), able_verb=able_verb, hero=definite(HERO)
    )

def gen_deficiency(impact):
    clauses = render_deficiency_clauses(impact["lost_edges"])
    become_verb = conjugate_verb_nlp("أصبح", AXIS_FEM, aspect='perf')
    if not clauses: return f"ف{become_verb} {AXIS} تعاني."
    first, *rest = clauses
    body = f"لا يوجد من {first}"
    for i, c in enumerate(rest):
        body += f" {'و لا حتى من' if i == len(rest) - 1 else 'و لا من'} {c}"
    return random.choice(STORY_LEXICON["deficiency_intros"]).format(become_verb=become_verb, axis=AXIS.strip(), body=body)

def gen_realization():
    feel_verb = conjugate_verb_nlp("شعر", AXIS_FEM, aspect='perf')
    return f"{feel_verb} {AXIS} بخطئ{pron(AXIS_FEM)} و بأهمية {definite(HERO)}، لكن بعد فوات الأوان."

def gen_hero_return(roles, pool, by_source):
    place = roles["المكان"]
    place_str = "مملكة البيولوجيا" if place == "غير محدد" else f"مملكة {place}"
    appear_verb = conjugate_verb_nlp("ظهر", HERO_FEM, aspect='perf')
    take = pool[:2]
    remaining = pool[2:]
    descriptions = render_witness_group(take, by_source)
    others_phrase = f" من {' و '.join(descriptions)}" if descriptions else ""
    text = random.choice(STORY_LEXICON["hero_return_intros"]).format(
        appear_verb=appear_verb, hero=definite(HERO), hero_pron=pron(HERO_FEM), axis=AXIS.strip(), others=others_phrase, place=place_str
    )
    return text, remaining

def gen_apology_and_forgiveness(pool, by_source):
    seize_verb = conjugate_verb_nlp("انتهز", AXIS_FEM, aspect='perf')
    initiate_verb = conjugate_verb_nlp("بادر", AXIS_FEM, aspect='perf')
    take1 = pool[:1]
    remaining = pool[1:]
    advice_desc = render_witness_group(take1, by_source)
    advice_phrase = f" بعد أن {conjugate_verb_nlp('سمع', AXIS_FEM, aspect='perf')} نصيحة {advice_desc[0]}" if advice_desc else ""
    opening = random.choice(STORY_LEXICON["apology_open_lines"]).format(axis=AXIS.strip(), seize_verb=seize_verb, initiate_verb=initiate_verb, advice=advice_phrase)
    
    if remaining:
        last_desc = render_witness_group([remaining[-1]], by_source)[0]
        reject_verb = "لم " + conjugate_verb_nlp("رفض", HERO_FEM, aspect='imperf')
        accept_verb = conjugate_verb_nlp("قبل", HERO_FEM, aspect='perf')
        repeat_verb = conjugate_verb_nlp("كرر", AXIS_FEM, aspect='imperf')
        closing = f"و {reject_verb} {definite(HERO)} بدور{pron(HERO_FEM)} نصيحة {last_desc} .. إذ {accept_verb} الاعتذار شرط أن لا {repeat_verb} {AXIS.strip()} خطأ{pron(AXIS_FEM)}"
    else:
        know_verb = conjugate_verb_nlp("علم", HERO_FEM, aspect='imperf')
        closing = f"و لأن {definite(HERO)} {know_verb} بأن {AXIS.strip()} {fem_adj('طيب', AXIS_FEM)} من الداخل.. {conjugate_verb_nlp('قبل', HERO_FEM, aspect='perf')} {definite(HERO)} الاعتذار شرط ألا {conjugate_verb_nlp('كرر', AXIS_FEM, aspect='imperf')} {AXIS.strip()} خطأ{pron(AXIS_FEM)}"
    return f"{opening} {closing}.."

def gen_hero_restoration(impact):
    clauses = render_restoration_clauses(impact["lost_edges"])
    return f"و بهذا {conjugate_verb_nlp('عاد', HERO_FEM, aspect='perf')} {definite(HERO)} إلى المملكة، و {' و '.join(clauses)} كما اعتاد من قبل.."

def gen_resolution():
    return "و عاد السلام و التآلف بين أهالي المملكة، في كيانٍ واحدٍ متكامل لا يشوبه تفرّقٌ أبدًا."


def render_former_duties(nodes, by_source):
    descriptions = []
    for node in nodes:
        node_fem = is_feminine_nlp(node)
        rel_pronoun = "التي" if node_fem else "الذي"
        used_to = "اعتادت" if node_fem else "اعتاد"
        clauses = []
        for relation, target in by_source.get(node, []):
            verb = conjugate_relation_nlp(relation, node_fem)
            clauses.append(verb if target.strip() in relation else f"{verb} {target}")
        body = " و ".join(clauses)
        for node in nodes:
         node_fem = is_feminine_nlp(node)
         rel_pronoun = "التي" if node_fem else "الذي"
         used_to = "اعتادت" if node_fem else "اعتاد"
         node_relations = [r for r, _ in by_source.get(node, [])]
         needs_pronoun = not (node_relations and all(relation_is_comparative(r) for r in node_relations))
         clauses = []
        for relation, target in by_source.get(node, []):
         verb = conjugate_relation_nlp(relation, node_fem)
         clauses.append(verb if target.strip() in relation else f"{verb} {target}")
        body = " و ".join(clauses)
        text = f"{node.strip()} {rel_pronoun} {used_to} أن {body}" if needs_pronoun else f"{node.strip()} {body}"
        descriptions.append(text)
    return descriptions

def gen_discord(G):
    rival = next((c.strip() for c in MAIN_CHARS if c.strip() not in (AXIS.strip(), HERO.strip())), "أحد المقربين")
    edge = find_rival_edge(G, AXIS, rival)
    action_phrase = ""
    if edge:
        u, v, relation = edge
        u_fem = is_feminine_nlp(u)
        verb = conjugate_relation_nlp(relation, u_fem)
        action_phrase = f" حيث {'اعتادت' if u_fem else 'اعتاد'} {u.strip()} أن {verb}،" if v.strip() in verb else f" ف{verb} {u.strip()} {v.strip()}،"
    return f"{action_phrase} {random.choice(STORY_LEXICON['discord_actions']).format(axis=AXIS.strip(), rival=rival)} {random.choice(STORY_LEXICON['division_descriptions'])}"

def gen_hero_plan(G):
    text_plan = render_plan_clauses(G)
    return f"لكن {definite(HERO)} لم {conjugate_verb_nlp('يأتي', HERO_FEM, aspect='imperf')} مكتوف اليدين.. فقد {conjugate_verb_nlp('جاء', HERO_FEM, aspect='perf')} و بجعبت{pron(HERO_FEM)} خطة محكمة، أساسها التعاون بين أهل المملكة، {text_plan}."

def render_plan_clauses(G):
    clauses = []
    for u, v, d in G.edges(data=True):
        relation = d["relation"]
        u_fem = is_feminine_nlp(u)
        verb = conjugate_relation_nlp(relation, u_fem)
        if relation_is_comparative(relation): clauses.append(f"أن {definite(u)} {relation.strip()} {definite(v)}")
        elif relation.strip() == "تتعاون": clauses.append(f"أن {verb} {definite(u)} مع {definite(v)}")
        elif v.strip() in verb: clauses.append(f"أن يقوم {definite(u)} بـ {verb}")
        else: clauses.append(f"أن {verb} {definite(u)} {definite(v)}")
    random.shuffle(clauses)
    if not clauses: return "تعتمد على إعادة النظام للمملكة"
    if len(clauses) == 1: return f"حيث يجب {clauses[0]}"
    return f"حيث يجب {clauses[0]}, كما يجب " + ", كما يجب ".join(clauses[1:-1]) + f"، وأخيراً يجب {clauses[-1]}"

def gen_pivot_neglect(conflicts):
    sentences = []
    for c in conflicts:
        actor = c["actor"].strip()
        actor_fem = is_feminine_nlp(actor)
        relation = c["action_edge"]["relation"]
        target = c["action_edge"]["target"].strip()
        verb = conjugate_relation_nlp(relation, actor_fem)
        clause = relation if target in relation else (f"{verb}{pron(AXIS_FEM)}" if target == AXIS.strip() else f"{verb} {target}")
        sentences.append(f"{'لم تعد' if actor_fem else 'لم يعد'} {definite(actor)} {clause}")
    actors_str = " و ".join(definite(c["actor"].strip()) for c in conflicts)
    return f"{random.choice(STORY_LEXICON['neglect_disasters']).format(actors=actors_str, axis=AXIS.strip())} إذ {' و '.join(sentences)}.. {random.choice(STORY_LEXICON['neglect_consequences']).format(axis=AXIS.strip())}"

def gen_hero_revenge(conflicts):
    sentences = []
    for c in conflicts:
        actor = c["actor"].strip()
        for edge in c.get("reaction_edges", []):
            verb = conjugate_relation_nlp(edge["relation"], HERO_FEM)
            sentences.append(f"لم يعد {definite(HERO)} {verb} {definite(actor)}")
    return f"{random.choice(STORY_LEXICON['revenge_intros']).format(hero=definite(HERO), axis=AXIS.strip())} {' و '.join(sentences)}."

def gen_final_reconciliation(conflicts, roles):
    place_str = "مملكة البيولوجيا" if roles["المكان"] == "غير محدد" else f"مملكة {roles['المكان']}"
    restored = []
    for c in conflicts:
        actor = c["actor"].strip()
        actor_fem = is_feminine_nlp(actor)
        relation = c["action_edge"]["relation"]
        target = c["action_edge"]["target"].strip()
        verb = conjugate_relation_nlp(relation, actor_fem)
        restored.append(relation if target in relation else (f"{verb}{pron(AXIS_FEM)}" if target == AXIS.strip() else f"{verb} {target}"))
        for edge in c.get("reaction_edges", []):
            restored.append(f"{conjugate_relation_nlp(edge['relation'], HERO_FEM)} {actor}")
    actors_str = " و ".join(definite(c["actor"].strip()) for c in conflicts)
    return f"فاعتذرت {actors_str} لـ{AXIS.strip()} بصدق، ف{'سامحتها' if AXIS_FEM else 'سامحها'}.. عندها فقط قبل {definite(HERO)} اعتذارها، و عادت كل العلاقات كما كانت: {' و '.join(restored)}. {random.choice(STORY_LEXICON['reconciliation_closings']).format(place=place_str)}"

def build_full_witness_pool(G, exclude):
    order = []
    by_source = {}
    for u, v, d in G.edges(data=True):
        if u in exclude: continue
        if u not in by_source: order.append(u)
        by_source.setdefault(u, []).append((d["relation"], v))
    return order, by_source

def choose_primary_conflict(conflicts):
    if not conflicts: return None
    for c in conflicts:
        if HERO.strip() in [r.strip() for r in c.get("reactors", [])]: return c
    return conflicts[0]

def gen_intro_civil_war(roles):
    place_str = "مملكة البيولوجيا" if roles["المكان"] == "غير محدد" else f"مملكة {roles['المكان']}"
    return f"{random.choice(STORY_LEXICON['intros'])} و في {place_str} التي عرف أهلها بالتآلف و المحبة سابقًا، {random.choice(STORY_LEXICON['disasters'])}"

def find_rival_edge(G, axis, rival):
    for u, v, d in G.edges(data=True):
        if (u == axis and v == rival) or (u == rival and v == axis): return u, v, d["relation"]
    return None

def gen_call_for_help(pool, by_source):
    take = pool[:2]
    return f"{random.choice(STORY_LEXICON['night_descriptions'])} مما دفع أهالي المملكة مثل {' و '.join(render_former_duties(take, by_source)) if take else 'بعض الأهالي'} إلى الاستعانة بقوى خارجية بالخفاء و ذلك لحل النزاع.", pool[2:]

def gen_hero_choice():
    return f"و كان خيارهم الوحيد هو {definite(HERO)}، الذي حالما وصل إلى المملكة {random.choice(STORY_LEXICON['hero_realization'])}"

def gen_civil_war_resolution(rival):
    return f"و بالفعل.. اتفق{'ت' if AXIS_FEM else ''} {AXIS.strip()} و {rival or 'الشخصية الرئيسية'} على تنفيذ الخطة و هزما قوى الشر معًا.. و بذلك عادت المملكة إلى سابق عهدها، بدون أي مشاكل أو ضغائن."

def gen_suffering_and_apology_demand(conflicts):
    actors_str = " و ".join(definite(c["actor"].strip()) for c in conflicts)
    return f"{random.choice(STORY_LEXICON['suffering_intros']).format(actors=actors_str, axis=AXIS.strip(), hero=definite(HERO))} {random.choice(STORY_LEXICON['apology_demand']).format(hero=definite(HERO), axis=AXIS.strip())}"

def build_story_graph(G_domain, impact, roles):
    G = nx.DiGraph()
    pool, by_source = build_witness_pool(G_domain, impact)
    negative_traits_text, pool = gen_negative_traits(pool, by_source)
    hero_return_text, pool = gen_hero_return(roles, pool, by_source)
    beats = [
        ("intro", gen_intro(G_domain, roles), False),
        ("negative_traits", negative_traits_text, True),
        ("false_confidence", gen_false_confidence(), True),
        ("deficiency", gen_deficiency(impact), True),
        ("realization", gen_realization(), True),
        ("hero_return", hero_return_text, True),
        ("apology_forgiveness", gen_apology_and_forgiveness(pool, by_source), True),
        ("hero_restoration", gen_hero_restoration(impact), True),
        ("resolution", gen_resolution(), True),
    ]
    for i, (name, text, mentions_hero) in enumerate(beats):
        G.add_node(name, text=text, mentions_hero=mentions_hero)
        if i > 0: G.add_edge(beats[i - 1][0], name)
    return G, beats[0][0]

def build_civil_war_graph(G_domain, roles):
    G = nx.DiGraph()
    rival = next((c.strip() for c in MAIN_CHARS if c.strip() not in (AXIS.strip(), HERO.strip())), None)
    pool, by_source = build_full_witness_pool(G_domain, exclude=({AXIS, HERO, rival} if rival else {AXIS, HERO}))
    call_text, pool = gen_call_for_help(pool, by_source)
    beats = [
        ("intro_discord", gen_intro_civil_war(roles) + gen_discord(G_domain), False),
        ("call_for_help", call_text, False),
        ("hero_choice", gen_hero_choice(), True),
        ("hero_plan", gen_hero_plan(G_domain), True),
        ("resolution", gen_civil_war_resolution(rival), True),
    ]
    for i, (name, text, mentions_hero) in enumerate(beats):
        G.add_node(name, text=text, mentions_hero=mentions_hero)
        if i > 0: G.add_edge(beats[i - 1][0], name)
    return G, beats[0][0]

def build_neglect_revenge_graph(G_domain, roles, conflicts):
    G = nx.DiGraph()
    beats = [
        ("intro", gen_intro(G_domain, roles), False),
        ("neglect", gen_pivot_neglect(conflicts), False),
        ("hero_revenge", gen_hero_revenge(conflicts), True),
        ("suffering_apology_demand", gen_suffering_and_apology_demand(conflicts), True),
        ("reconciliation", gen_final_reconciliation(conflicts, roles), True),
    ]
    for i, (name, text, mentions_hero) in enumerate(beats):
        G.add_node(name, text=text, mentions_hero=mentions_hero)
        if i > 0: G.add_edge(beats[i - 1][0], name)
    return G, beats[0][0]

def assert_hero_not_first(G, start_node):
    if G.nodes[start_node]["mentions_hero"]: raise ValueError("انتهاك للقاعدة: البطل مذكور في بداية الحكاية!")

def generate_story(G, start_node):
    assert_hero_not_first(G, start_node)
    order = list(nx.topological_sort(G))
    return "\n\n".join(G.nodes[n]["text"] for n in order)

def build_auto_story_graph(G_domain, impact, roles, conflicts):
    plot_choices = [
        lambda: build_story_graph(G_domain, impact, roles),
        lambda: build_civil_war_graph(G_domain, roles),
    ]
    if conflicts: plot_choices.append(lambda: build_neglect_revenge_graph(G_domain, roles, conflicts))
    return random.choice(plot_choices)()

if __name__ == "__main__":
    G_story, start = build_auto_story_graph(G_domain, impact, roles, conflicts)
    print(generate_story(G_story, start))