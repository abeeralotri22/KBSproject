import json
import os

# external, growing lexicon — not inline code. Science-lesson relation verbs

ONTOLOGY_PATH = os.path.join(
    os.path.dirname(__file__), "antonym_ontology.json")
with open(ONTOLOGY_PATH, "r", encoding="utf-8") as f:
    ANTONYMS = json.load(f)

# pure positional/locative facts don't negate at all
POSITIONAL_MARKERS = {"في", "فيها", "فيه", "خلف", "خلفها", "أمام", "أمامها",
                      "فوق", "فوقها", "تحت", "تحتها", "بجانب", "بجانبها",
                      "مقابل", "الى", "إلى"}


NON_NEGATABLE_MARKERS = {"بسبب", "لفتح", "لأن", "لان", "لكي", "كي", "حتى",
                         "من أجل", "من اجل", "مثال", "مثاله", "مثالها", "تجعل"}


def is_non_negatable(relation):
    return any(relation == m or relation.startswith(m + " ")
               for m in NON_NEGATABLE_MARKERS)


def _looks_like_verb(word):
    # ي/ت/ن/أ/إ are unambiguous present-tense verb prefixes
    # "الـ"-prefixed definite noun , exclude
    # "ا" elsewhere (انثناؤها, اهتزازه) is a real masdar
    return word.startswith(("ي", "ت", "ن", "أ", "إ")) or (
        word.startswith("ا") and not word.startswith("ال"))


def is_positional(relation):
    words = relation.split(" ")
    if words[0] not in POSITIONAL_MARKERS:
        return False
    return not any(_looks_like_verb(w) for w in words[1:])


def negate_relation(relation):

    relation = relation.strip()
    if is_positional(relation) or is_non_negatable(relation):
        return relation
    if relation in ANTONYMS:
        return ANTONYMS[relation]
    # a root match replaces the WHOLE relation, not a spliced-in substring.
    # keys under 3 characters are skipped here — too short to be a safe
    # substring root (e.g. "هي"  as a substring  also matches inside "تنتهي"
    for key, antonym in ANTONYMS.items():
        if len(key) >= 3 and key in relation:
            return antonym
    # already a negative phrase in the source (e.g. "لم ينجح") — its antonym
    # is the affirmative, so strip the negation instead of returning it
    for neg_prefix in ("لا ", "لم "):
        if relation.startswith(neg_prefix):
            return relation[len(neg_prefix):].strip()
    # already negative via "غير" its antonym is dropping "غير"
    if " غير " in f" {relation} ":
        return relation.replace("غير ", "", 1).strip()
    # a leading modal "قد" , negate the verb itself
    if relation.startswith("قد "):
        return f"لا {relation[len('قد '):].strip()}"
    # some relations open with a noun+pronoun subject before their verb
    # (اهتزازه يبدل, انثناؤها يفتح, تقلصها يقارب)  "لا" must sit before the
    # verb, not the whole clause
    PREPOSITIONS = {"إلى", "الى", "على", "عن",
                    "في", "من", "مع", "حتى", "بـ", "لـ"}
    first, _, rest = relation.partition(" ")
    rest_first = rest.split(" ", 1)[0] if rest else ""
    if (rest and first.endswith(("ه", "ها", "هما", "هم", "هن"))
            and rest_first not in PREPOSITIONS
            and _looks_like_verb(rest_first)):
        # negate both the noun-subject and its verb ("عدم اهتزازه لا يبدل")
        return f"عدم {first} لا {rest}"

    if _looks_like_verb(relation.split(" ", 1)[0]):
        return f"لا {relation}"
    return f"غير {relation}"


def negate_concept(label):
    """
    Antonym/negation for a NODE (usually a noun/masdar phrase describing an
    event, e.g. "إهمال الأسنان"). Fallback prefixes "عدم" (absence-of) —
    grammatically masculine regardless of the noun that follows, which also
    keeps anything built on top of the negated concept gender-safe.
    """
    label = label.strip()
    if label in ANTONYMS:
        return ANTONYMS[label]
    if label.startswith("عدم "):
        return label
   # dropping "غير"
    if " غير " in f" {label} ":
        return label.replace("غير ", "", 1).strip()
    return f"عدم {label}"


EVENT_TYPES = {"حدث", "احداث", "فعل"}
STATE_TYPES = {"نوع", "عملية", "عملية حيوية"}


def negate_by_type(label, node_type):
    if node_type in EVENT_TYPES:
        return negate_concept(label)
    if node_type in STATE_TYPES:
        return f"عدم وجود {label}"
    return label
