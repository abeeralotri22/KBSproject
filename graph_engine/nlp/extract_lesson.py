
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

HERE = Path(__file__).resolve().parent
INPUT_TEXT_PATH = HERE / "input_text.txt"
OUTPUT_PATH = HERE / "llm_output.json"
ARCHIVE_DIR = HERE / "archive"
ONTOLOGY_PATH = HERE.parent / "sna" / "antonym_ontology.json"
JUDY_API_URL = "https://judy4444-text2tale-nlp.hf.space/generate_graph"


KNOWN_TEXTS_DIR = HERE / "known_texts"

sys.path.insert(0, str(HERE.parent / "sna"))
from archetype import CAUSAL_MARKERS  # noqa: E402 — same list new_sna_impact2.py's classify_chain_subtype uses


LOAD_BEARING_TYPES = ["حدث", "احداث", "فعل", "نوع", "عملية", "عملية حيوية",
                      "مكان", "زمان"]
OTHER_COMMON_TYPES = ["اشخاص", "مادة", "عضو", "نظام", "كائن", "مفهوم", "عنصر"]

SYSTEM_INSTRUCTION = f"""أنت مساعد متخصص في استخراج المخططات المعرفية (Knowledge Graphs) من نصوص عربية تعليمية وسردية، لمشروع اسمه text2tale يحوّل الدروس إلى مخططات قصصية.

ستُعطى: (1) النص الأصلي، (2) استخراج أولي خام من نظام آلي ضعيف الجودة (فيه أخطاء كثيرة). مهمتك إعادة بناء الاستخراج بشكل صحيح تمامًا اعتمادًا على النص الأصلي — لا تثق بالاستخراج الخام، استخدمه فقط كمرجع تقريبي للعقد والعلاقات المحتملة.

أعد الناتج بصيغة JSON فقط (بدون أي شرح أو نص إضافي)، بهذا الشكل بالضبط:
{{
  "subject": "علوم" أو "تاريخ" أو "جغرافيا",
  "nodes": [{{"id": "عقدة_1", "label": "...", "type": "..."}}],
  "edges": [{{"source": "عقدة_1", "target": "عقدة_2", "type": "..."}}]
}}

قواعد إلزامية:

1. "subject": حدد نوع الدرس بدقة: علوم (أحياء/كيمياء/فيزياء...) أو تاريخ أو جغرافيا. هذا الحقل إلزامي ويجب أن يكون أول مفتاح في الملف.

2. العقد (nodes) يجب أن تكون كيانات حقيقية فقط (أشخاص، أماكن، مواد، أعضاء، مفاهيم، أحداث محددة، عمليات) — وليست جملًا أو عبارات فعلية طويلة أو أحداثًا مركبة. مثال خطأ: "وجود ليفيات" أو "قطع الحجارة الضخمة" كعقدة — الصح: "ليفيات" و"الحجارة الضخمة" ككيانات، والفعل (وجود/قطع) يصبح نوع العلاقة (edge type) بين عقدتين، وليس جزءًا من التسمية.

3. لا تكرر التسمية (label) كنوع (type) — هذا خطأ شائع في الاستخراج الخام يجب تصحيحه دائمًا. اختر نوعًا حقيقيًا من هذه القائمة إن أمكن: {", ".join(LOAD_BEARING_TYPES)} — أو من هذه الأنواع الشائعة الأخرى إذا لم تنطبق: {", ".join(OTHER_COMMON_TYPES)}. يمكنك استخدام نوع آخر مناسب غير مذكور إن لزم، لكن ممنوع أن يكون النوع نسخة من التسمية.
   - "فعل": سلوك أو ممارسة أو تصرف يقوم به شخص أو شيء (إهمال الأسنان، الرعي الجائر، إدارة خاطئة) — عادة مصدر من وزن إفعال/تفعيل يصف تصرفًا وليس شيئًا ثابتًا.
   - "حدث": واقعة وقعت في لحظة زمنية محددة ولها بداية ونهاية (ثورة، حرب، مؤتمر).
   - "نوع" أو "عملية"/"عملية حيوية": حالة متغيرة أو آلية مستمرة تجري باستمرار (هضم، تفاعلات بيئية، الحرارة، الرطوبة، نخر السن) — لا فرق فعليًا بين نوع وعملية في هذا النظام، اختر الأنسب دلاليًا.
   - "زمان": أي تاريخ أو سنة أو فترة زمنية مذكورة — اجعلها عقدة منفصلة عن الحدث نفسه، لا تدمجها في تسمية عقدة أخرى.
   - "مكان": أي موقع جغرافي أو مبنى أو منطقة.
   - تحذير مهم: لا تستخدم "مفهوم" كنوع افتراضي عندما تتردد. "مفهوم" مخصص فقط لفكرة مجردة حقيقية بلا فاعل ولا تغيّر (كالجاذبية أو الديمقراطية كفكرة عامة) — أي شيء يمكن أن "يحدث" أو "يُهمَل" أو "يتراكم" أو له فاعل يقوم به هو فعل أو نوع/عملية أو حدث، وليس مفهومًا. معظم الحالات لا تحتاج "مفهوم" إطلاقًا.

4. أسماء العقد يجب أن تكون قصيرة ومحددة (كلمة أو كلمتين إلى ثلاث كحد أقصى عادة) — ليست عبارات طويلة أو جملًا كاملة.

5. علاقات الحواف (edge type) يجب أن تكون قصيرة ومختصرة (فعل أو عبارة فعلية قصيرة) — وليست جملًا طويلة.

6. الرسم البياني الناتج يجب أن يكون متصلًا بالكامل (غراف مترابط) — كل عقدة يجب أن تصل إلى بقية العقد عبر مسار من الحواف (في أي اتجاه)، لا عقد معزولة ولا مكونات منفصلة. إذا كان النص يذكر حقائق متوازية تبدو غير مرتبطة ظاهريًا، ابحث عن علاقة منطقية تربطها (مثلاً كلاهما يخص نفس الموضوع أو المكان أو الشخص الرئيسي) بدلاً من تركها معزولة.

7. لا تدمج كيانين مختلفين في تسمية واحدة (مثال خطأ من الاستخراج الخام: "أهرامات القدماء المصريون الجيزة" — هذا دمج خاطئ لعقدتين).

8. لا تُنشئ أكثر من علاقة واحدة بين نفس زوج العقدتين (في أي من الاتجاهين) إلا إذا كانت العلاقتان تصفان حقيقتين مختلفتين فعلاً ذكرهما النص صراحةً. مثال خطأ: "الدب القطبي --[يمتلك فراء يتألف من]--> الشعر الأولي" ثم أيضاً "الشعر الأولي --[طوله يتراوح على جسم]--> الدب القطبي" — هاتان الحافتان تصفان نفس العلاقة (فراء الدب) مرتين باتجاهين متعاكسين بدلاً من علاقة واحدة واضحة؛ اختر الاتجاه والصياغة الأنسب لما ذكره النص واحذف التكرار.

9. استخدم "عقدة_1", "عقدة_2", ... كمعرّفات (id) بالترتيب.

أعد الناتج كـ JSON صالح فقط، بلا Markdown fencing وبلا أي نص قبله أو بعده."""


# few-shot examples — shown to the model as real prior turns, not just
# described in prose. Prose rules alone left the model free to reinvent
# entity/edge granularity differently on every call; a concrete pattern to
# match against collapses most of that swing. One example per domain +
# archetype combo actually in use: تاريخ/hub, جغرافيا/hub, علوم/causal-chain.
FEW_SHOT_EXAMPLES = [
    (
        """تسابقت بريطانيا وفرنسا للسيطرة على مصر؛ لأهمية موقعها على طريق الهند التجاري ووفرة ثرواتها، فأرسلت فرنسا حملة عسكرية قادها نابليون بونابرت عام 1798م؛ لكنها اضطرت للانسحاب عام 1801م بتأثير المقاومة الشعبية، وتحالف بريطانيا مع السلطان العثماني.
وازداد اهتمام بريطانيا بمصر بعد افتتاح قناة السويس، وظهور الأزمة المالية التي أدت إلى ازدياد التدخل الأجنبي. وهذا ما أدى إلى قيام ثورة أحمد عرابي عام 1881م.""",
        {
            "subject": "تاريخ",
            "nodes": [
                {"id": "عقدة_1", "label": "بريطانيا", "type": "اشخاص"},
                {"id": "عقدة_2", "label": "فرنسا", "type": "اشخاص"},
                {"id": "عقدة_3", "label": "مصر", "type": "مكان"},
                {"id": "عقدة_4", "label": "طريق الهند التجاري", "type": "مكان"},
                {"id": "عقدة_5", "label": "نابليون بونابرت", "type": "اشخاص"},
                {"id": "عقدة_6", "label": "الحملة العسكرية الفرنسية", "type": "اشخاص"},
                {"id": "عقدة_7", "label": "1798", "type": "زمان"},
                {"id": "عقدة_8", "label": "1801", "type": "زمان"},
                {"id": "عقدة_9", "label": "المقاومة الشعبية", "type": "فعل"},
                {"id": "عقدة_10", "label": "السلطان العثماني", "type": "اشخاص"},
                {"id": "عقدة_11", "label": "قناة السويس", "type": "مكان"},
                {"id": "عقدة_12", "label": "الأزمة المالية", "type": "نوع"},
                {"id": "عقدة_13", "label": "التدخل الأجنبي", "type": "نوع"},
                {"id": "عقدة_14", "label": "ثورة أحمد عرابي", "type": "حدث"},
                {"id": "عقدة_15", "label": "أحمد عرابي", "type": "اشخاص"},
                {"id": "عقدة_16", "label": "1881", "type": "زمان"},
            ],
            "edges": [
                {"source": "عقدة_1", "target": "عقدة_3",
                    "type": "تسابقت للسيطرة على"},
                {"source": "عقدة_2", "target": "عقدة_3",
                    "type": "تسابقت للسيطرة على"},
                {"source": "عقدة_3", "target": "عقدة_4", "type": "تقع على"},
                {"source": "عقدة_2", "target": "عقدة_6", "type": "أرسلت"},
                {"source": "عقدة_5", "target": "عقدة_6", "type": "قاد"},
                {"source": "عقدة_6", "target": "عقدة_3", "type": "استهدفت"},
                {"source": "عقدة_6", "target": "عقدة_7", "type": "بدأت في"},
                {"source": "عقدة_6", "target": "عقدة_8", "type": "انسحبت في"},
                {"source": "عقدة_9", "target": "عقدة_6",
                    "type": "أجبرت على الانسحاب"},
                {"source": "عقدة_1", "target": "عقدة_10", "type": "تحالفت مع"},
                {"source": "عقدة_11", "target": "عقدة_1",
                    "type": "افتتاحها زاد اهتمام"},
                {"source": "عقدة_12", "target": "عقدة_13", "type": "أدت إلى ازدياد"},
                {"source": "عقدة_13", "target": "عقدة_14", "type": "أدى إلى قيام"},
                {"source": "عقدة_15", "target": "عقدة_14", "type": "قاد"},
                {"source": "عقدة_14", "target": "عقدة_16", "type": "وقعت في"},
                {"source": "عقدة_12", "target": "عقدة_3", "type": "وقعت في"},
                {"source": "عقدة_1", "target": "عقدة_13", "type": "جزء من"},
            ],
        },
    ),
    (
        """يعتمد قطاع الإنتاج الحيواني في سورية بشكل أساس على الأغنام والأبقار والماعز لإنتاج الحليب واللحوم الحمراء والجلود والصوف، وهي أيضاً عامل استقرار اقتصادي واجتماعي للمجتمع الريفي، الذي يُعدّ حيازة المواشي وتربيتها نمطاً معيشياً أساسياً فيه، في حين ينتشر نمط الرعي المتنقل على مناطق واسعة من سورية ولاسيّما على باديتها، وكثيراً ما يتأثر إنتاجها بتذبذب أعداد الحيوانات بسبب موجات الجفاف، وتوفير الخدمات البيطرية في معظم مناطق سورية.""",
        {
            "subject": "جغرافيا",
            "nodes": [
                {"id": "عقدة_1", "label": "قطاع الإنتاج الحيواني", "type": "نظام"},
                {"id": "عقدة_2", "label": "سورية", "type": "مكان"},
                {"id": "عقدة_3", "label": "الأغنام", "type": "كائن"},
                {"id": "عقدة_4", "label": "الأبقار", "type": "كائن"},
                {"id": "عقدة_5", "label": "الماعز", "type": "كائن"},
                {"id": "عقدة_6", "label": "الحليب", "type": "مادة"},
                {"id": "عقدة_7", "label": "اللحوم الحمراء", "type": "مادة"},
                {"id": "عقدة_8", "label": "الجلود", "type": "مادة"},
                {"id": "عقدة_9", "label": "الصوف", "type": "مادة"},
                {"id": "عقدة_10", "label": "المجتمع الريفي", "type": "مكان"},
                {"id": "عقدة_11", "label": "المواشي", "type": "كائن"},
                {"id": "عقدة_12", "label": "الرعي المتنقل", "type": "نوع"},
                {"id": "عقدة_13", "label": "مناطق سورية", "type": "مكان"},
                {"id": "عقدة_14", "label": "بادية سورية", "type": "مكان"},
                {"id": "عقدة_15", "label": "موجات الجفاف", "type": "نوع"},
                {"id": "عقدة_16", "label": "أعداد الحيوانات", "type": "نوع"},
                {"id": "عقدة_17", "label": "الخدمات البيطرية", "type": "نظام"},
            ],
            "edges": [
                {"source": "عقدة_1", "target": "عقدة_2", "type": "في"},
                {"source": "عقدة_1", "target": "عقدة_3",
                    "type": "يعتمد بشكل أساسي على"},
                {"source": "عقدة_1", "target": "عقدة_4",
                    "type": "يعتمد بشكل أساسي على"},
                {"source": "عقدة_1", "target": "عقدة_5",
                    "type": "يعتمد بشكل أساسي على"},
                {"source": "عقدة_1", "target": "عقدة_6", "type": "لإنتاج"},
                {"source": "عقدة_1", "target": "عقدة_7", "type": "لإنتاج"},
                {"source": "عقدة_1", "target": "عقدة_8", "type": "لإنتاج"},
                {"source": "عقدة_1", "target": "عقدة_9", "type": "لإنتاج"},
                {"source": "عقدة_11", "target": "عقدة_10",
                    "type": "عامل استقرار اقتصادي واجتماعي لـ"},
                {"source": "عقدة_10", "target": "عقدة_11", "type": "حيازة وتربية"},
                {"source": "عقدة_12", "target": "عقدة_13", "type": "ينتشر في"},
                {"source": "عقدة_12", "target": "عقدة_14", "type": "ولا سيما في"},
                {"source": "عقدة_15", "target": "عقدة_16", "type": "تذبذب"},
                {"source": "عقدة_16", "target": "عقدة_11", "type": "يؤثر في إنتاج"},
                {"source": "عقدة_17", "target": "عقدة_13", "type": "تُوفر في"},
                {"source": "عقدة_11", "target": "عقدة_3", "type": "تشمل"},
                {"source": "عقدة_11", "target": "عقدة_4", "type": "تشمل"},
                {"source": "عقدة_11", "target": "عقدة_5", "type": "تشمل"},
                {"source": "عقدة_14", "target": "عقدة_2", "type": "جزء من"},
                {"source": "عقدة_13", "target": "عقدة_2", "type": "جزء من"},
            ],
        },
    ),
    (
        """يؤدي التدخين إلى تراكم مادة القطران في الرئتين. يهيّج القطران الأنسجة الرئوية، مما يسبب التهاباً مزمناً فيها. يؤدي الالتهاب المزمن إلى تلف الحويصلات الهوائية، وقد يتطور ذلك إلى مرض انتفاخ الرئة.""",
        {
            "subject": "علوم",
            "nodes": [
                {"id": "عقدة_1", "label": "التدخين", "type": "فعل"},
                {"id": "عقدة_2", "label": "القطران", "type": "مادة"},
                {"id": "عقدة_3", "label": "الرئتين", "type": "عضو"},
                {"id": "عقدة_4", "label": "الأنسجة الرئوية", "type": "عضو"},
                {"id": "عقدة_5", "label": "التهاب مزمن", "type": "نوع"},
                {"id": "عقدة_6", "label": "الحويصلات الهوائية", "type": "عضو"},
                {"id": "عقدة_7", "label": "انتفاخ الرئة", "type": "نوع"},
            ],
            "edges": [
                {"source": "عقدة_1", "target": "عقدة_2", "type": "يؤدي إلى تراكم"},
                {"source": "عقدة_2", "target": "عقدة_3", "type": "يتراكم في"},
                {"source": "عقدة_2", "target": "عقدة_4", "type": "يهيّج"},
                {"source": "عقدة_4", "target": "عقدة_5", "type": "إصابتها تسبب"},
                {"source": "عقدة_5", "target": "عقدة_6", "type": "يؤدي إلى تلف"},
                {"source": "عقدة_6", "target": "عقدة_7", "type": "تلفها يتطور إلى"},
            ],
        },
    ),
]


LINEAR_SHAPE_DIRECTIVE = """
ملاحظة مهمة عن الشكل البنيوي: هذا النص يصف {kind} — استخرجه كمسار خطي واحد قدر الإمكان:
- نقطة بداية واحدة (لا عدة بدايات مستقلة).
- كل خطوة/نتيجة تتصل بالخطوة التالية بشكل متسلسل (خطي)، وليس عدة مصادر منفصلة تتقارب في عقدة واحدة.
- لا تُدخل عقدة بحيث يكون لها أكثر من مصدر واحد (in-degree) إلا إذا كان النص يصرّح بوضوح أن هذه العقدة نتيجة لعدة مصادر مستقلة حقًا.
- لا تُنشئ تفرعًا (عقدة بها أكثر من علاقة صادرة) إلا إذا كان النص يصف صراحةً نتيجتين مختلفتين لنفس الخطوة — وتجنّب التقاء الفرعين مرة أخرى في نفس العقدة لاحقًا ما لم يقل النص ذلك بوضوح.
- استخدم صياغة العلاقات كما وردت في النص بالضبط: لا تخترع كلمات سببية (يؤدي/يسبب) إن كان النص يصف مجرد ترتيب أو تتابع (ثم/بعد ذلك/تنتقل إلى) وليس سببًا ونتيجة فعليين.
هدفك مسار يشبه سلسلة تسوس الأسنان في المثال الثالث أعلاه: مسار واحد مستقيم من البداية إلى النهاية.
"""

HUB_SHAPE_DIRECTIVE = """
ملاحظة مهمة عن الشكل البنيوي: هذا النص لا يصف سلسلة سببية ولا مسارًا متتابعًا — يبدو أنه نص وصفي يذكر عدة حقائق مستقلة عن موضوع مركزي واحد (كوصف عضو أو مكان أو نظام). استخرجه كبنية "محور" واحدة قدر الإمكان:
- حدد الكيان المركزي الذي يدور حوله النص (كالعضو أو المكان الرئيسي).
- اربط كل حقيقة مستقلة مباشرة بالكيان المركزي كعلاقة صادرة أو واردة منه، بدلاً من ربط الحقائق ببعضها في سلسلة طويلة.
- لا تُنشئ سلسلة من العقد المتتالية (أ يؤدي إلى ب يؤدي إلى ج...) إلا إذا كان النص فعلاً يصف تتابعًا زمنيًا أو سببيًا صريحًا بين تلك الحقائق تحديدًا.
- عدد الحقائق/الفروع الصادرة من الكيان المركزي يجب أن يعكس فقط ما ذكره النص صراحةً — لا تُقسّم حقيقة واحدة إلى عدة عقد وهمية لزيادة عدد الفروع، ولا تدمج حقائق متعددة في عقدة واحدة لتقليلها.
هدفك بنية تشبه مثال الإنتاج الحيواني (المثال الثاني أعلاه): كيان مركزي واحد تتفرع منه الحقائق مباشرة.
"""

# ordering/pathway language — "starts with X... ends with Y", "then",
# "next stage" — signals a sequence-chain (process/pathway) rather than a
# hub of independent facts, even with zero causal wording. مسار السمع and
# المعدة both use exactly this framing ("تبدأ بـ...وتنتهي بـ...").
# "بـ" is a proclitic that fuses directly onto the next word with no space
# ("تبدأ باختناق", not "تبدأ بـ اختناق") — matching "تبدأ بـ" would miss the
# far more common fused form, so the marker drops the preposition and
# matches on the verb alone.
SEQUENCE_MARKERS = ["يبدأ", "تبدأ", "ينتهي", "تنتهي", "ثم ", "بعد ذلك",
                    "يليه", "تليها", "المرحلة التالية", "ينتقل إلى", "تنتقل إلى",
                    "يمر", "تمر", "أولاً", "ثانياً", "لاحقًا"]


def detect_causal(text):
    return any(marker in text for marker in CAUSAL_MARKERS)


def detect_sequence(text):
    return any(marker in text for marker in SEQUENCE_MARKERS)


def shape_directive(text):
    if detect_causal(text):
        return "shape/causal", LINEAR_SHAPE_DIRECTIVE.format(kind="علاقة سببية (سبب←نتيجة)")
    if detect_sequence(text):
        return "shape/sequence", LINEAR_SHAPE_DIRECTIVE.format(kind="مسارًا أو تتابعًا مرتبًا من الخطوات")
    return "shape/hub", HUB_SHAPE_DIRECTIVE


def call_judy_api(text):
    try:
        response = requests.post(
            JUDY_API_URL, json={"text": text}, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(
            f"تحذير: تعذر الوصول لخدمة judy ({e}) — سنكمل بدون استخراج أولي.")
        return None


def _log_retry(retry_state):
    exc = retry_state.outcome.exception()
    wait = retry_state.next_action.sleep
    print(f"الخادم مزدحم (503) — إعادة المحاولة {retry_state.attempt_number}/5 "
          f"بعد {wait:.0f} ثانية... ({exc})")


@retry(
    retry=retry_if_exception_type(ServerError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    before_sleep=_log_retry,
    reraise=True,
)
def call_gemini(text, judy_raw, api_key):
    client = genai.Client(api_key=api_key)

    # few-shot examples as real prior turns (not text baked into the system
    # prompt) — the model pattern-matches structured example turns far more
    # reliably than a wall of prose rules with JSON quoted inside it.
    contents = []
    for example_text, example_json in FEW_SHOT_EXAMPLES:
        contents.append(types.Content(
            role="user",
            parts=[types.Part(
                text=f"النص الأصلي:\n{example_text}\n\nالاستخراج الأولي الخام:\n(غير متوفر)")],
        ))
        contents.append(types.Content(
            role="model",
            parts=[types.Part(text=json.dumps(
                example_json, ensure_ascii=False))],
        ))

    judy_context = (
        json.dumps(judy_raw, ensure_ascii=False, indent=2)
        if judy_raw else "(غير متوفر)"
    )
    _, shape_note = shape_directive(text)
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=f"""النص الأصلي:
{text}
{shape_note}
الاستخراج الأولي الخام (لا تثق به، استخدمه كمرجع تقريبي فقط):
{judy_context}""")],
    ))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            response_mime_type="application/json",
            max_output_tokens=32768,
            # "thinking" models spend part of max_output_tokens on internal
            # reasoning before writing the visible answer — for a structured
            # extraction task we don't need chain-of-thought, so turn it off
            # entirely and let the whole budget go to the actual JSON.
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    reason = response.candidates[0].finish_reason if response.candidates else None
    if reason and str(reason) not in ("STOP", "FinishReason.STOP"):
        print(
            f"تحذير: finish_reason={reason} (قد يعني توقفًا مبكرًا أو حجبًا)")
    if not response.text:
        raise RuntimeError(
            f"Gemini أعاد استجابة بدون نص (finish_reason={reason}).")
    return response.text


def extract_json(raw_text):
    raw_text = raw_text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_text, re.DOTALL)
    if fenced:
        raw_text = fenced.group(1)
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        # show exactly where it broke instead of an opaque traceback —
        # usually either truncation (response cut off mid-JSON) or a stray
        # unescaped character from the model
        start = max(0, e.pos - 200)
        end = min(len(raw_text), e.pos + 200)
        print(f"\nفشل تحليل JSON عند الموضع {e.pos} — السياق حول الخطأ:")
        print("..." + raw_text[start:end] + "...")
        print(f"\nطول الاستجابة الكامل: {len(raw_text)} حرفًا")
        raise


def validate_and_report(data):
    problems = []
    if "subject" not in data:
        problems.append("لا يوجد حقل subject")
    ids = {n["id"] for n in data.get("nodes", [])}
    for n in data.get("nodes", []):
        if n.get("type", "").strip() == n.get("label", "").strip():
            problems.append(f"عقدة '{n.get('label')}' نوعها مطابق لتسميتها")

    import networkx as nx
    G = nx.Graph()
    G.add_nodes_from(ids)
    for e in data.get("edges", []):
        if e["source"] in ids and e["target"] in ids:
            G.add_edge(e["source"], e["target"])
    n_components = nx.number_connected_components(
        G) if G.number_of_nodes() else 0
    if n_components > 1:
        problems.append(
            f"الغراف غير متصل بالكامل — {n_components} مكونات منفصلة")

    id_to_label = {n["id"]: n["label"] for n in data.get("nodes", [])}
    seen_pairs = {}
    for e in data.get("edges", []):
        pair = frozenset((e["source"], e["target"]))
        if len(pair) < 2:
            continue  # self-loop, not a duplicate-pair case
        if pair in seen_pairs:
            a, b = id_to_label.get(e["source"], e["source"]), id_to_label.get(
                e["target"], e["target"])
            problems.append(
                f"علاقتان بين نفس الزوج ({a} <-> {b}) — تكرار محتمل، راجع إن كانتا حقيقتين مختلفتين فعلاً")
        else:
            seen_pairs[pair] = e

    return problems


def check_ontology_coverage(data):
    with open(ONTOLOGY_PATH, encoding="utf-8") as f:
        ontology = json.load(f)
    missing = []
    for e in data.get("edges", []):
        rel = e["type"].strip()
        covered = rel in ontology or any(k in rel for k in ontology)
        if not covered:
            missing.append(rel)
    return missing


def _normalize(text):
    return " ".join(text.split())


def find_known_match(text):
    """
    If input_text.txt matches a known_texts/<name>.txt (whitespace-
    normalized), return the path to the corresponding nlp/<name>.json.
    Returns None if no known_texts folder entry matches, or the JSON is
    missing (nothing crashes — falls back to the API path either way).
    """
    if not KNOWN_TEXTS_DIR.is_dir():
        return None
    target = _normalize(text)
    for known_file in KNOWN_TEXTS_DIR.glob("*.txt"):
        if _normalize(known_file.read_text(encoding="utf-8")) == target:
            json_path = HERE / f"{known_file.stem}.json"
            if json_path.exists():
                return json_path
            print(
                f"تحذير: تطابق نصي مع {known_file.name} لكن {json_path.name} غير موجود.")
    return None


def main():
    if not INPUT_TEXT_PATH.exists():
        INPUT_TEXT_PATH.write_text("", encoding="utf-8")
        print(f"الصق نص الدرس في {INPUT_TEXT_PATH} ثم أعد التشغيل.")
        sys.exit(1)

    text = INPUT_TEXT_PATH.read_text(encoding="utf-8").strip()
    if not text:
        print(f"الملف {INPUT_TEXT_PATH} فارغ — الصق نص الدرس فيه أولًا.")
        sys.exit(1)

    known_json = find_known_match(text)
    if known_json:
        print(
            f"تطابق مع نص معروف — نسخ {known_json.name} مباشرة (بدون استدعاء API).")
        data = json.loads(known_json.read_text(encoding="utf-8"))
        output_str = json.dumps(data, ensure_ascii=False, indent=2)
        OUTPUT_PATH.write_text(output_str, encoding="utf-8")
        print(f"تم الحفظ في {OUTPUT_PATH}")
        problems = validate_and_report(data)
        if problems:
            print("\n=== مشاكل يجب مراجعتها ===")
            for p in problems:
                print(" -", p)
        missing = check_ontology_coverage(data)
        if missing:
            print(
                f"\n=== علاقات غير موجودة في antonym_ontology.json ({len(missing)}) ===")
            for m in sorted(set(missing)):
                print(" -", m)
        return

    api_key = os.environ.get("Bana_API_KEY")
    if not api_key:
        print("خطأ: لم يتم ضبط Bana_API_KEY.")
        print('في PowerShell: $env:Bana_API_KEY="your-key-here"')
        print("احصل على مفتاح مجاني من: https://aistudio.google.com/apikey")
        sys.exit(1)

    print("جاري استخراج أولي عبر judy...")
    judy_raw = call_judy_api(text)

    shape_kind, _ = shape_directive(text)
    shape_labels = {
        "shape/causal": "تم رصد صياغة سببية — سيُطلب من Gemini بناء سلسلة سببية خطية.",
        "shape/sequence": "تم رصد صياغة تتابع/مسار — سيُطلب من Gemini بناء سلسلة خطية (تسلسل وليس سببية بالضرورة).",
        "shape/hub": "لم تُرصد صياغة سببية أو تتابع — سيُطلب من Gemini بناء بنية محور (hub) حول كيان مركزي.",
    }
    print(shape_labels[shape_kind])

    print("جاري التصحيح عبر Gemini...")
    raw_response = call_gemini(text, judy_raw, api_key)
    data = extract_json(raw_response)

    output_str = json.dumps(data, ensure_ascii=False, indent=2)
    OUTPUT_PATH.write_text(output_str, encoding="utf-8")
    print(f"\nتم الحفظ في {OUTPUT_PATH}")

    # keep a permanent, timestamped copy too — llm_output.json gets
    # overwritten every run, so without this a bad/interesting run's exact
    # output is gone the moment you run it again
    ARCHIVE_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = ARCHIVE_DIR / f"{stamp}.json"
    archive_path.write_text(output_str, encoding="utf-8")
    print(f"نسخة محفوظة في {archive_path}")

    problems = validate_and_report(data)
    if problems:
        print("\n=== مشاكل يجب مراجعتها ===")
        for p in problems:
            print(" -", p)
    else:
        print("\nلا مشاكل بنيوية ظاهرة (الغراف متصل، لا تكرار للتسمية كنوع).")

    missing = check_ontology_coverage(data)
    if missing:
        print(
            f"\n=== علاقات غير موجودة في antonym_ontology.json ({len(missing)}) ===")
        print("هذه لن تُضاف تلقائيًا — راجعها يدويًا:")
        for m in sorted(set(missing)):
            print(" -", m)
    else:
        print("\nكل العلاقات مغطاة في antonym_ontology.json.")


if __name__ == "__main__":
    main()
