import json
import os
import random
from typing import Optional, List, Dict, Tuple
from camel_tools.morphology.database import MorphologyDB
from camel_tools.morphology.analyzer import Analyzer

try:
    db = MorphologyDB.builtin_db()
    analyzer = Analyzer(db)
except Exception as e:
    analyzer = None
    print(f"تنبيه: تعذر تحميل Camel Tools ({e}). سيتم الاعتماد على القواعد الثابتة فقط.")


def is_female_name(word: str) -> bool:
    if not word:
        return False

    clean_word = word.strip()

    if clean_word.endswith("ة") or clean_word.endswith("ت"):
        return True

    if analyzer:
        analyses = analyzer.analyze(clean_word)
        for analysis in analyses:
            if analysis.get("gen") == "f":
                return True

    return False


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean(text) -> str:
    return " ".join(str(text).strip().split())


def load_antonym_graph(antonym_plot_path: str, antonym_chain_filename: str = "antonym_chain.json") -> dict:
    try:
        return load_json(antonym_plot_path)
    except FileNotFoundError:
        try:
            fallback_path = os.path.join(os.path.dirname(antonym_plot_path) or ".", antonym_chain_filename)
            return load_json(fallback_path)
        except FileNotFoundError:
            return {}


NO_DEFINITE_PARTICLES = {
    "لا", "من", "في", "على", "إلى", "الى", "عن", "مع", "أو", "او", "و", "ثم",
    "بل", "لكن", "إذا", "أن", "إن", "قد", "لم", "لن", "ما", "حتى", "غير",
    "بين", "دون", "عند", "ف", "ب", "ل", "ك",
}

DEFINITE_PREFIX = "ال"
LA_PREFIX = "اللا"
NEGATION_STARTERS = {"عدم", "لا", "لم", "لن", "ما", "غير"}


def _add_definite(word: str) -> str:
    if not word or word in NO_DEFINITE_PARTICLES or word.startswith(DEFINITE_PREFIX):
        return word
    return DEFINITE_PREFIX + word


def definite_label(label) -> str:
    words = [w for w in clean(label).split(" ") if w]
    if words and words[0] in NEGATION_STARTERS:
        return clean(label)
    result: List[str] = []
    i = 0
    n = len(words)
    while i < n:
        w = words[i]
        if w == "لا" and i + 1 < n:
            result.append(LA_PREFIX)
            result.append(words[i + 1])
            i += 2
            continue
        result.append(_add_definite(w))
        i += 1
    return " ".join(result)


class PhraseBank:
    def __init__(self, phrases: List[str], rng: random.Random):
        self._all = phrases
        self._rng = rng
        self._pool: List[str] = []
        self._refill()

    def _refill(self):
        self._pool = self._all[:]
        self._rng.shuffle(self._pool)

    def get(self) -> str:
        if not self._pool:
            self._refill()
        return self._pool.pop()


class DramaticEngine:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.dramatic_catalysts = {
                    "DISPUTE": {
                        "causes": [
                            "نشوب خلاف حاد بين {hero} و{main_char} حول إدارة المهام",
                            "سوء فهم طارئ بين {hero} و{main_char} أدى إلى استياء متبادل",
                            "تصاعد التوتر بين {hero} و{main_char} بسبب الضغط المفاجئ"
                        ],
                        "actions": [
                            "{h_decide} {hero} الرحيل فوراً عن",
                            "{h_withdraw} {hero} غاضباً {h_leaving} {main_char} في",
                            "{h_refuse} {hero} الاستمرار في التعاون مع {main_char} داخل"
                        ],
                        "resolutions": [
                            "{h_backpedal} {hero} عن موقفه بعد تدارك الأمر مع {main_char} {h_agree} على التفاهم حول",
                            "{h_accept} {hero} و{main_char} الاعتذار وعادت المياه إلى مجاريها في",
                            "{h_reach} {hero} و{main_char} إلى تسوية ملموسة أزالت الخلاف واستعادت"
                        ]
                    },
                
                    "BURNOUT": {
                        "causes": [
                            "الإرهاق الشديد ونفاذ الموارد أثناء مساندة {hero} لـ {main_char}",
                            "تزايد الأحمال على {hero} و{main_char} بشكل تجاوز القدرة الاستيعابية",
                            "استمرار العمل المتواصل بين {hero} و{main_char} دون فترة راحة كافية"
                        ],
                        "actions": [
                            "{h_stop} {hero} قسراً عن العطاء في",
                            "{h_fall} {hero} {h_tired} أمام {main_char} في غيابة",
                            "{h_enter} {hero} في حالة خمول {h_leaving} {main_char} {m_manage}"
                        ],
                        "resolutions": [
                            "{h_recover} {hero} نشاطه بمساعدة {main_char} {h_return_to} إلى",
                            "{h_receive} {hero} الدعم اللازم من {main_char} {h_resume} دوره في",
                            "{h_overcome} {hero} مرحلة الإجهاد وعاد ليدعم {main_char} في"
                        ]
                    },
                
                    "EXTERNAL_INTERFERENCE": {
                        "causes": [
                            "تسلل عنصر غريب أربك التنسيق بين {hero} و{main_char}",
                            "تأثير ظروف بيئية طارئة باعدت بين {hero} و{main_char}",
                            "تغير مفاجئ في البيئة تسبب في قطيعة بين {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_isolate} {hero} تماماً عن {main_char} في",
                            "{h_distract} انتباه {hero} بعيداً عن {main_char} و",
                            "{h_lose} {hero} قدرته على التواصل مع {main_char} داخل"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من إزالة المؤثر الخارجي و{both_return} للتواصل في",
                            "{both_overcome} {hero} برفقة {main_char} على العائق الطارئ و{both_restore} ارتباطهما بـ",
                            "{both_succeed} {hero} و{main_char} في تطهير البيئة من الدخيل ليستقر الوضع مجدداً في"
                        ]
                    },
                
                    "MISTRUST": {
                        "causes": [
                            "ظهور تسريبات معلوماتية غامضة جعلت {hero} يشك في نوايا {main_char}",
                            "اختفاء بعض الوثائق الأساسية مما أثار الريبة بين {hero} و{main_char}",
                            "تضارب البيانات المقدمة مما جعل {hero} يرتاب في خطوات {main_char}"
                        ],
                        "actions": [
                            "{h_isolate} {hero} نفسه لمراجعة الحسابات والتصرفات بعيداً عن {main_char} في",
                            "{h_refuse} {hero} مشاركة الخطط الجوهرية مع {main_char} داخل",
                            "{h_withdraw} {hero} إلى منطقة آمنة لمراقبة تحركات {main_char} في"
                        ],
                        "resolutions": [
                            "{both_restore} {hero} و{main_char} الثقة المتبادلة بعد كشف الحقيقة واحتواء",
                            "{h_accept} {hero} إيضاحات {main_char} وانجلت الشكوك تماماً حول",
                            "{both_succeed} {hero} و{main_char} في كشف الفاعل الحقيقي وإعادة ترتيب"
                        ]
                    },
                
                    "RIVALRY": {
                        "causes": [
                            "بروز رغبة مفاجئة لدى {hero} في إثبات الأسبقية على {main_char}",
                            "تنافس غير معلن حول أحقية قيادة المبادرة بين {hero} و{main_char}",
                            "محاولة {hero} التفوق الفردي وتحقيق مكاسب مستقلة عن {main_char}"
                        ],
                        "actions": [
                            "{h_decide} {hero} خوض السباق بشكل منفرد وترك {main_char} في",
                            "{h_refuse} {hero} توحيد الجهود مراهناً على قدراته الخاصة داخل",
                            "{h_enter} {hero} في تحدٍّ علني مجازفاً بعلاقته مع {main_char} في"
                        ],
                        "resolutions": [
                            "{h_backpedal} {hero} عن الفردية و{h_agree} مع {main_char} على التكامل في",
                            "{both_manage} {hero} و{main_char} من تحويل التنافس إلى تعاون مثمر أدى لتطوير",
                            "{h_reach} {hero} و{main_char} إلى قناعة بأن قوتهما في اتحادهما لإنجاح"
                        ]
                    },
                
                    "HESITATION": {
                        "causes": [
                            "خوف {hero} الشديد من عواقب القرار المقبل على مستقبل {main_char}",
                            "تردد {hero} في حسم الموقف بسبب مخاطر عالية يخشى تداعياتها على {main_char}",
                            "شديد القلق الذي تملك {hero} جراء ضخامة التحدي الذي يواجهه مع {main_char}"
                        ],
                        "actions": [
                            "{h_stop} {hero} عن اتخاذ أي خطوة جريئة مما جمد حركة {main_char} في",
                            "{h_withdraw} {hero} مؤقتاً لتفادي تحمل مسؤولية الفشل أمام {main_char} داخل",
                            "{h_lose} {hero} المبادرة وتراجع خطوة إلى الخلف مفسحاً المجال لـ {main_char} في"
                        ],
                        "resolutions": [
                            "{h_receive} {hero} التشجيع والجرأة من {main_char} و{h_resume} خوض التحدي في",
                            "{h_overcome} {hero} مخاوفه الذاتية وبادر بالخطوة الأولى مستنداً إلى دعم {main_char} في",
                            "{both_succeed} {hero} و{main_char} في كسر حاجز الخوف وتجاوز العقبات في"
                        ]
                    },
                
                    "MISINFORMATION": {
                        "causes": [
                            "انتشار شائعات كاذبة أربكت حسابات {hero} وشوهت صورة {main_char}",
                            "وصول تقارير مغلوطة إلى {hero} تتهم {main_char} بالتراجع عن التعهدات",
                            "انخداع {hero} بمعلومات مزيفة هدفت لضرب التنسيق مع {main_char}"
                        ],
                        "actions": [
                            "{h_decide} {hero} إيقاف خطة التوسع واعتماد الحذر تجاه {main_char} في",
                            "{h_refuse} {hero} تنفيذ التعليمات الصادرة بالتنسيق مع {main_char} داخل",
                            "{h_isolate} {hero} الفريق تماماً تجنباً للتسريبات المفترضة من {main_char} في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من تفنيد الشائعات وإثبات الحقائق في",
                            "{h_accept} {hero} الحقائق الموثقة التي قدمها {main_char} واعتذر عن استعجاله في",
                            "{both_succeed} {hero} و{main_char} في كشف مصدر التضليل واستعادة سلامة"
                        ]
                    },
                
                    "PRIORITY_SHIFT": {
                        "causes": [
                            "تغير طارئ في الاستراتيجية جعل {hero} يركز على هدف يختلف عن هدف {main_char}",
                            "انشغال {hero} بملف مفاجئ أبعده عن مسار العمل المشترك مع {main_char}",
                            "تضارب الأولويات المرحلية بين رؤية {hero} وتطلعات {main_char}"
                        ],
                        "actions": [
                            "{h_distract} انتباه {hero} نحو المسار الجديد تركاً {main_char} يواجه التحدي في",
                            "{h_withdraw} {hero} اهتمامه المباشر {h_leaving} {main_char} {m_manage} الأمور بمفرده في",
                            "{h_enter} {hero} في مسار مستقل دون تنسيق سابق مع {main_char} داخل"
                        ],
                        "resolutions": [
                            "{both_reach} {hero} و{main_char} إلى موازنة تضمن دمج الأولويات في",
                            "{h_backpedal} {hero} عن التحيز لخطته الموازية و{h_agree} مع {main_char} على العودة إلى",
                            "{both_restore} {hero} و{main_char} التوافق الاستراتيجي وعادا للعمل كيد واحدة في"
                        ]
                    },
                
                    "PSYCHOLOGICAL_PRESSURE": {
                        "causes": [
                            "شعور {hero} بثقل المسؤولية وخوفه من خيبة أمل {main_char}",
                            "ضغوط نفسية متزايدة جعلت {hero} يتصرف بحساسية مفرطة تجاه {main_char}",
                            "تراكم الانتقادات الخارجية التي أثرت سلبياً على معنويات {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_fall} {hero} تحت تأثير الانفعال {h_leaving} {main_char} في حيرة داخل",
                            "{h_stop} {hero} عن التواصل والدخول في حالة من الانعزال عن {main_char} في",
                            "{h_withdraw} {hero} مؤقتاً لاستعادة التوازن بعيداً عن ضغوط {main_char} في"
                        ],
                        "resolutions": [
                            "{h_recover} {hero} ثباته الانفعالي بفضل مساندة {main_char} و{h_return_to} إلى",
                            "{both_overcome} {hero} و{main_char} الضغوط النفسية عبر جلسات الحوار المصارحة في",
                            "{h_receive} {hero} التشجيع الكافي لكسر حالة العزلة والعودة بقوة إلى"
                        ]
                    },
                
                    "TECHNICAL_ERROR": {
                        "causes": [
                            "وقوع خطأ غير مقصود من {hero} أدى لتلف جزئي في العمل الذي يبنيه {main_char}",
                            "تطبيق إجراء خاطئ من قبل {hero} أربك المنظومة التي يديرها {main_char}",
                            "سوء استخدام للوسائل المتاحة من {hero} تسبب في إرباك خطط {main_char}"
                        ],
                        "actions": [
                            "{h_enter} {hero} في حالة ارتباك محاولاً التغطية على الخلل أمام {main_char} في",
                            "{h_refuse} {hero} اعترافه المباشر بالخطأ خوفاً من عتاب {main_char} داخل",
                            "{h_isolate} {hero} موقع الخلل محاولاً إصلاحه بمفرده دون علم {main_char} في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من تدارك الخطأ الفني وإعادة تصحيح",
                            "{h_accept} {hero} الشجاعة للاعتراف بالخطأ وشاركه {main_char} في ترميم",
                            "{both_succeed} {hero} و{main_char} في تحديث آليات العمل لتفادي تكرار الخلل في"
                        ]
                    },
                
                    "OVERCONFIDENCE": {
                        "causes": [
                            "شغف {hero} بالانتصارات السابقة مما أفقده الحذر وتجاهل نصائح {main_char}",
                            "اندفاع {hero} غير المدروس واستهانته بالصعوبات ورأي {main_char}",
                            "ثقة {hero} المفرطة التي جعلته يتجاوز الصلاحيات المتفق عليها مع {main_char}"
                        ],
                        "actions": [
                            "{h_decide} {hero} المضي قدماً في مغامرة غير محسوبة مجاهلاً {main_char} في",
                            "{h_refuse} {hero} الاستماع للتحذيرات صاماً أذنيه عن تنبيهات {main_char} داخل",
                            "{h_lose} {hero} السيطرة الميدانية نتيجة الاندفاع مما أربك {main_char} في"
                        ],
                        "resolutions": [
                            "{h_backpedal} {hero} عن غروره بعد الانتكاسة الأولى و{h_agree} على التواضع لـ {main_char} في",
                            "{h_receive} {hero} نصيحة حكيمة من {main_char} أعادته إلى صوابه لإصلاح",
                            "{both_restore} {hero} و{main_char} التوازن والتخطيط العقلاني لضمان استقرار"
                        ]
                    },
                
                    "RESOURCE_SCARCITY": {
                        "causes": [
                            "نقص حاد في المستلزمات الأساسية أثار منافسة غير مقصودة بين {hero} و{main_char}",
                            "شح الإمكانيات المتاحة مما فرض على {hero} التنازل أو الضغط على {main_char}",
                            "شح الإمدادات الطارئة التي تهدد استمرار مشروع {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_decide} {hero} احتكار الموارد المتبقية لحماية موقعه دون {main_char} في",
                            "{h_withdraw} {hero} من المشاركة الجماعية خوفاً من نفاد حصته أمام {main_char} في",
                            "{h_stop} {hero} عن تقديم الدعم المعتاد لـ {main_char} بسبب القلة في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من ابتكار بدائل جديدة تجاوزا بها شح",
                            "{h_reach} {hero} و{main_char} إلى تقاسم عادل ومتكافئ للموارد المتاحة في",
                            "{both_succeed} {hero} و{main_char} في توفير مصادر إضافية أنقذت"
                        ]
                    },
                
                    "RELIANCE": {
                        "causes": [
                            "اعتماد {hero} المفرط على جهود {main_char} دون تقديم إضافة حقيقية",
                            "اتكال {hero} الكلي على قدرات {main_char} مما أدى لثقل الكاهل",
                            "تهرب {hero} التدريجي من المسؤوليات القائمة وتحميلها لـ {main_char}"
                        ],
                        "actions": [
                            "{h_enter} {hero} في حالة اتكالية تام {h_leaving} {main_char} {m_manage} الصعاب في",
                            "{h_distract} اهتمامه نحو الأمور الثانوية وترك الجهد الأكبر لـ {main_char} في",
                            "{h_refuse} {hero} القيام بحصته المقررة متعللاً بالظروف أمام {main_char} داخل"
                        ],
                        "resolutions": [
                            "{h_resume} {hero} تحمل مسؤولياته كاملة بعد تحذير صريح من {main_char} في",
                            "{h_overcome} {hero} سبيلي الخمول واستعاد زمام المبادرة ليدعم {main_char} في",
                            "{both_restore} {hero} و{main_char} مبدأ العدالة وتوزيع الأدوار للنهوض بـ"
                        ]
                    },
                
                    "DOGMATISM": {
                        "causes": [
                            "تمسك {hero} الصارم بموقفه ورفضه لأي مرونة يقترحها {main_char}",
                            "جمود الرؤية لدى {hero} ومقاومته للتغييرات التطويرية التي طرحها {main_char}",
                            "تصلب رأي {hero} وإصراره على تطبيق أسلوبه الخاص على {main_char}"
                        ],
                        "actions": [
                            "{h_refuse} {hero} النقاش كلياً وقطع قنوات الاستماع لـ {main_char} في",
                            "{h_isolate} {hero} مقترحات {main_char} والعمل وفق رؤيته المفردة داخل",
                            "{h_decide} {hero} فرض شروطه التعجيزية للتعاون مع {main_char} في"
                        ],
                        "resolutions": [
                            "{h_accept} {hero} مرونة الأفكار بعد اقتناعه بالأدلة المعروضة من {main_char} في",
                            "{both_reach} {hero} و{main_char} إلى صيغة توفيقية جمعت بين الآراء في",
                            "{h_backpedal} {hero} عن تشبثه واستفاد من المقترحات البناءة لـ {main_char} في"
                        ]
                    },
                
                    "INFILTRATION": {
                        "causes": [
                            "اكتشاف ثغرة أمنية تسبب بها تساهل {hero} ونبه إليها {main_char}",
                            "تسرب شفرات أو معلومات سرية أضعف موقف {hero} و{main_char}",
                            "استغلال أطراف محايدة لغياب الحذر عند {hero} للإضرار بـ {main_char}"
                        ],
                        "actions": [
                            "{h_lose} {hero} السيطرة على حماية البيانات مما وضع {main_char} في خطر داخل",
                            "{h_withdraw} {hero} مذهولاً من حجم الخرق الشديد في",
                            "{h_enter} {hero} في حالة استنفار ودفاع سلبياً محاولاً حماية {main_char} في"
                        ],
                        "resolutions": [
                            "{both_succeed} {hero} و{main_char} في سد الثغرات وإغلاق منافذ الخطر في",
                            "{h_overcome} {hero} بالتعاون مع {main_char} الآثار الجانبية واستعادا أمن",
                            "{both_restore} {hero} و{main_char} الحماية المطلوبة وأعادا تنظيم"
                        ]
                    },
                
                    "UNFULFILLED_PROMISES": {
                        "causes": [
                            "عجز {hero} عن الإيفاء بعهد قطع على نفسه لصالح {main_char}",
                            "تأخر {hero} في تسليم مخرجات وعد بها {main_char} في الموعد المحدد",
                            "إخلاف {hero} لالتزام أساسي تسبب في تعطيل خطط {main_char}"
                        ],
                        "actions": [
                            "{h_withdraw} {hero} خجلاً من مواجهة {main_char} في",
                            "{h_refuse} {hero} تقديم مبررات واهية تجنباً للمواجهة مع {main_char} داخل",
                            "{h_isolate} {hero} نفسه لحين البحث عن مخرج يرضي {main_char} في"
                        ],
                        "resolutions": [
                            "{h_receive} {hero} مهلة جديدة من {main_char} ونجح في الإيفاء بعهده في",
                            "{h_accept} {hero} التعويض عن التأخير وتقديم خدمات مضاعفة لـ {main_char} في",
                            "{both_restore} {hero} و{main_char} الثقة بعد إنجاز التعهدات وتجاوز"
                        ]
                    },
                
                    "SUDDEN_ACCELERATION": {
                        "causes": [
                            "تسارع وتيرة الأحداث بشكل لم يستطع {hero} مجاراته برفقة {main_char}",
                            "انهمار الطلبات الطارئة التي تجاوزت سرعة استجابة {hero} و{main_char}",
                            "تغير الجداول الزمنية بشكل مفاجئ ضغط على خطة {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_lose} {hero} القدرة على مواكبة المتطلبات وتخلف عن {main_char} في",
                            "{h_fall} {hero} في حيرة من أمره {h_leaving} {main_char} يصارع الوقت داخل",
                            "{h_stop} {hero} عن المتابعة بسبب كثرة التشتت والتسارع في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من ضبط إيقاع العمل واستعادة التنسيق في",
                            "{h_recover} {hero} تركيزه السريع وقاد عملية الإنقاذ برفقة {main_char} في",
                            "{both_succeed} {hero} و{main_char} في تجاوز السباق الزمني وتنظيم"
                        ]
                    },
                
                    "METHODOLOGY_CLASH": {
                        "causes": [
                            "صدام بين أسلوب {hero} التقليدي وطريقة {main_char} الحديثة",
                            "اختلاف النهج العملي المتبع بين {hero} و{main_char} في التنفيذ",
                            "تباين طريقة إدارة الأزمات لدى {hero} مقارنة بمنهجية {main_char}"
                        ],
                        "actions": [
                            "{h_refuse} {hero} اتباع الأساليب المبتكرة متمسكاً بالقديم أمام {main_char} في",
                            "{h_withdraw} {hero} من النقاشات المنهجية مفضلاً العمل المستقل عن {main_char} داخل",
                            "{h_decide} {hero} إثبات صحة نهجه من خلال تجربة منفردة بعيداً عن {main_char} في"
                        ],
                        "resolutions": [
                            "{both_reach} {hero} و{main_char} إلى دمج الأساليب في منهجية هجينة ناجحة لـ",
                            "{h_accept} {hero} تطعيم طريقته بأفكار {main_char} لتحسين جودة",
                            "{both_succeed} {hero} و{main_char} في ابتكار أسلوب مشترك أفضل لتطوير"
                        ]
                    },
                
                    "MISCALCULATION": {
                        "causes": [
                            "تقدير خاطئ من {hero} للظروف المحيطة تسبب في إحراج {main_char}",
                            "استهانة {hero} بالصعوبات اللوجستية التي حذر منها {main_char}",
                            "قراءة غير دقيقة من {hero} للمخاطر أثرت سلباً على موقف {main_char}"
                        ],
                        "actions": [
                            "{h_fall} {hero} في مأزق بيئي حرج مسبباً الإرباك لـ {main_char} في",
                            "{h_lose} {hero} السيطرة على الموقف مما اضطر {main_char} للتدخل داخل",
                            "{h_withdraw} {hero} إلى نقطة الدفاع الأولى تاركاً المجال لـ {main_char} في"
                        ],
                        "resolutions": [
                            "{h_recover} {hero} بالتعاون مع {main_char} السيطرة الميدانية وأصلحا",
                            "{both_overcome} {hero} و{main_char} خطأ التقدير عبر خطة بديلة أنقذت",
                            "{both_succeed} {hero} و{main_char} في تصحيح المسار وإعادة الاستقرار لـ"
                        ]
                    },
                
                    "COMMUNICATION_BREAKDOWN": {
                        "causes": [
                            "انقطاع وسائل الاتصال المباشرة مما أدى لعدم وصول توجيهات {hero} إلى {main_char}",
                            "تشوش قنوات التنسيق بين {hero} و{main_char} بسبب ظروف خارجة عن الإرادة",
                            "تأخر الرسائل المتبادلة بين {hero} و{main_char} مما تسبب في قرارات متضاربة"
                        ],
                        "actions": [
                            "{h_lose} {hero} القدرة على إرسال الإشارات مما عزله عن {main_char} في",
                            "{h_isolate} {hero} نفسه في الميدان بانتظار عودة الاتصال مع {main_char} داخل",
                            "{h_enter} {hero} في حالة تصرف انفرادي لغياب التوجيه من {main_char} في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من إعادة فتح قنوات التواصل وإعادة",
                            "{both_restore} {hero} و{main_char} الربط المباشر وتداركا النتائج السلبية في",
                            "{both_succeed} {hero} و{main_char} في توحيد التحركات فور زوال الانقطاع في"
                        ]
                    },
                
                    "CONFLICT_OF_INTEREST": {
                        "causes": [
                            "تصادم المكاسب الشخصية لـ {hero} مع الأهداف العامة لـ {main_char}",
                            "ظهور عروض مغرية لـ {hero} تتناقض مع التزاماته تجاه {main_char}",
                            "تداخل المصالح الخارجية مما وضع {hero} في موقف حرج أمام {main_char}"
                        ],
                        "actions": [
                            "{h_decide} {hero} تقديم مصلحته الفردية مؤقتاً ومباغتة {main_char} في",
                            "{h_withdraw} {hero} من التزاماته السابقة تحسباً للخسارة مع {main_char} داخل",
                            "{h_refuse} {hero} التنازل عن مكاسبه الخاصة إرضاءً لـ {main_char} في"
                        ],
                        "resolutions": [
                            "{both_reach} {hero} و{main_char} إلى اتفاق متوازن يضمن مصالح الطرفين في",
                            "{h_backpedal} {hero} عن تقديم المكاسب الشخصية مضحياً بأطماعه لأجل {main_char} في",
                            "{both_succeed} {hero} و{main_char} في إعادة هيكلة الأهداف المشتركة لضمان"
                        ]
                    },
                
                    "SECRECY": {
                        "causes": [
                            "تكتم {hero} على خطوات جوهرية وإخفائها عن {main_char}",
                            "غموض سلوكيات {hero} الأخيرة مما أثار ريبة وخوف {main_char}",
                            "امتناع {hero} عن كشف حقيقة أوراقه بالكامل لـ {main_char}"
                        ],
                        "actions": [
                            "{h_isolate} {hero} تحركاته في الخفاء مبتعداً عن أعين {main_char} في",
                            "{h_refuse} {hero} الإفصاح عن دوافعه الحقيقية أمام استفسارات {main_char} داخل",
                            "{h_enter} {hero} في حالة غموض تام أربكت حسابات {main_char} في"
                        ],
                        "resolutions": [
                            "{h_accept} {hero} كشف كافة الأوراق وشرح أسباب السرية لـ {main_char} في",
                            "{both_restore} {hero} و{main_char} الشفافية المطلقة بعد زوال دواعي الكتمان في",
                            "{both_manage} {hero} و{main_char} من بناء جسر صراحة أصلح"
                        ]
                    },
                
                    "IDENTITY_CRISIS": {
                        "causes": [
                            "فقدان {hero} لثقته بإمكانياته وشعوره بأنه يستغل {main_char}",
                            "مرور {hero} بأزمة تشكيك في أهدافه وجدوى مساندته لـ {main_char}",
                            "تضارب القناعات الداخلية لدى {hero} مما أثر على أدائه مع {main_char}"
                        ],
                        "actions": [
                            "{h_withdraw} {hero} إلى عزلة ذاتية محاولاً إعادة اكتشاف نفسه بعيداً عن {main_char} في",
                            "{h_stop} {hero} عن أداء مهامه المعتادة تاركاً {main_char} يتساءل في",
                            "{h_fall} {hero} في حالة من التردد القاسي مما شل حركة {main_char} داخل"
                        ],
                        "resolutions": [
                            "{h_recover} {hero} يقينه بذاته بعد دعم معنوي كبير من {main_char} و{h_return_to} إلى",
                            "{h_overcome} {hero} صراعه الداخلي وعاد بأفكار أكثر نضجاً لخدمة {main_char} في",
                            "{both_succeed} {hero} و{main_char} في كسر التردد واستعادة الحماس لتطوير"
                        ]
                    },
                
                    "DATA_LEAK": {
                        "causes": [
                            "تسريب غير مقصود لخطط {main_char} بسبب غفلة {hero}",
                            "وقوع إستراتيجيات العمل المتبعة بين {hero} و{main_char} في أيدي الخصوم",
                            "استغلال نقطة ضعف في نظام حماية {hero} لإفشاء أسرار {main_char}"
                        ],
                        "actions": [
                            "{h_enter} {hero} في حالة طوارئ محاولاً إيقاف النزيف المعلوماتي دون {main_char} في",
                            "{h_lose} {hero} السيطرة على انتشار السر مما أفقد {main_char} المبادرة داخل",
                            "{h_isolate} {hero} المساحات المتأثرة خشية تفاقم الوضع أمام {main_char} في"
                        ],
                        "resolutions": [
                            "{both_succeed} {hero} و{main_char} في إغلاق مصدر التسريب واحتواء الأزمة في",
                            "{both_manage} {hero} و{main_char} من تحويل خطة العمل لتفادي آثار الكشف في",
                            "{h_accept} {hero} تحمل المسئولية وتعهده بإنشاء نظام حماية جديد لـ {main_char} في"
                        ]
                    },
                
                    "STRUCTURAL_CHANGE": {
                        "causes": [
                            "فرض قوانين جديدة أربكت خطة العمل المعتادة بين {hero} و{main_char}",
                            "إعادة توزيع الصلاحيات بشكل غير متوقع بين {hero} و{main_char}",
                            "تغير القواعد التنظيمية بشكل فجائي هدد موقع {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_refuse} {hero} الانصياع للهيكل الجديد وعبّر عن امتناعه لـ {main_char} في",
                            "{h_withdraw} {hero} خطوة للوراء رافضاً تحمل القواعد المفروضة على {main_char} داخل",
                            "{h_decide} {hero} التمرد على القوانين والتصرف بشكل فردي بـ"
                        ],
                        "resolutions": [
                            "{both_reach} {hero} و{main_char} إلى كيفية للتكيف مع القوانين الجديدة في",
                            "{h_backpedal} {hero} عن رفضه واستوعب متطلبات المرحلة بدعم من {main_char} في",
                            "{both_succeed} {hero} و{main_char} في استغلال الهيكل الجديد لصالح"
                        ]
                    },
                
                    "NEGLIGENCE": {
                        "causes": [
                            "تراخي {hero} في تنفيذ متابعة دورية تسببت في إخفاق لـ {main_char}",
                            "إهمال {hero} لمراجعة بعض التفاصيل الحاسمة الخاصة بـ {main_char}",
                            "تجاهل {hero} لملاحظة إنذار مبكر تسبب في تعقد موقف {main_char}"
                        ],
                        "actions": [
                            "{h_fall} {hero} في فخ التقصير {h_leaving} {main_char} يدفع الثمن في",
                            "{h_distract} انتباه {hero} بأمور جانبية مهتملاً التزاماته نحو {main_char} داخل",
                            "{h_stop} {hero} عن المتابعة مما أدى لتراكم الأخطاء على {main_char} في"
                        ],
                        "resolutions": [
                            "{h_accept} {hero} مقصريته وتدارك الفجوة عبر جهد مضاعف أنقذ {main_char} في",
                            "{both_manage} {hero} و{main_char} من إصلاح التلف الناتج عن التقصير في",
                            "{both_restore} {hero} و{main_char} الانضباط والرقابة لضمان جودة"
                        ]
                    },
                
                    "DECEPTION": {
                        "causes": [
                            "وقوع {hero} فريسة لخديعة أعدها طرف ثالث للإيقاع بـ {main_char}",
                            "استدراج {hero} في فخ مدروس أضر بمصداقيته أمام {main_char}",
                            "مكيدة خارجية نجحت في زرع الفرقة وتزييف الوقائع بين {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_decide} {hero} مواجهة المصيدة بمفرده بدلاً من إبلاغ {main_char} في",
                            "{h_lose} {hero} بوصلته نتيجة الخديعة مما أبعده عن دعم {main_char} داخل",
                            "{h_withdraw} {hero} متأثراً بالخديعة تاركاً {main_char} يواجه المجهول في"
                        ],
                        "resolutions": [
                            "{both_succeed} {hero} و{main_char} في كشف المؤامرة وإبطال الخديعة في",
                            "{h_recover} {hero} وعيه بالفخ بمساعدة {main_char} وأعادا بناء",
                            "{both_restore} {hero} و{main_char} قوة الحلف المشترك متجاوزين"
                        ]
                    },
                
                    "MISALLOCATION": {
                        "causes": [
                            "إسناد مهام يفوق قدرات {hero} مما شكل عبئاً في مساندة {main_char}",
                            "توزيع غير متكافئ للمسؤوليات تسبب في شعور {hero} بالمظلومية أمام {main_char}",
                            "تكليف {hero} بأدوار لا تناسب خبرته مما أثر على نتاج {main_char}"
                        ],
                        "actions": [
                            "{h_refuse} {hero} استكمال الأنشطة الصعبة ممتنعاً عن مساعدة {main_char} في",
                            "{h_stop} {hero} عن التنفيذ معلناً اعتراضه على آلية العمل مع {main_char} داخل",
                            "{h_enter} {hero} في إضراب جزئي معبراً عن رفضه لتحمل أعباء {main_char} في"
                        ],
                        "resolutions": [
                            "{both_reach} {hero} و{main_char} إلى إعادة توزيع المهام بإنصاف في",
                            "{h_accept} {hero} التكليف الجديد بعد تعديل الصلاحيات بالاتفاق مع {main_char} في",
                            "{both_succeed} {hero} و{main_char} في تحسين كفاءة العمل ورفع"
                        ]
                    },
                
                    "DEMORALIZATION": {
                        "causes": [
                            "تعرض {hero} لموجة محبطة من الانتقادات أضعفت عزيمته في الوقوف مع {main_char}",
                            "سماع {hero} لتقييمات سلبيات هدمت طاقته للإنجاز برفقة {main_char}",
                            "انتشار أجواء سلبية في بيئة العمل أثرت على حماس {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_fall} {hero} في حالة إحباط تام {h_leaving} {main_char} بلا سند في",
                            "{h_withdraw} {hero} عن الساحة متأثراً بالطاقة السلبية تجاه {main_char} داخل",
                            "{h_lose} {hero} شعلة الشغف وتوقف عن تشجيع {main_char} في"
                        ],
                        "resolutions": [
                            "{h_receive} {hero} تحفيزاً قوياً من {main_char} أعاد إليه الروح المعنوية في",
                            "{both_overcome} {hero} و{main_char} التأثير السلبي واستعادا شعلة الحماس لـ",
                            "{both_succeed} {hero} و{main_char} في خلق بيئة إيجابية دافعة نحو"
                        ]
                    },
                
                    "PROCRASTINATION": {
                        "causes": [
                            "تأجيل {hero} غير المبرر لخطوات حاسمة ينتظرها {main_char}",
                            "مماطلة {hero} في تجهيز المخرجات المطلوب تسليمها لـ {main_char}",
                            "بطء استجابة {hero} في إنهاء متطلبات العمل اليومي مع {main_char}"
                        ],
                        "actions": [
                            "{h_stop} {hero} عن الإنجاز المباشر مسوفاً المهام المقررة لـ {main_char} في",
                            "{h_distract} انتباهه بالفرعيات مهتملاً الموعد النهائي المحدد من {main_char} داخل",
                            "{h_enter} {hero} في حالة تباطؤ أضرت بالجدول الزمني الخاص بـ {main_char} في"
                        ],
                        "resolutions": [
                            "{h_resume} {hero} العمل بسرعة مضاعفة مستدركاً التأخير لصالح {main_char} في",
                            "{both_manage} {hero} و{main_char} من وضع خطة زمنية صارمة لتجاوز تسويف",
                            "{both_succeed} {hero} و{main_char} في إنهاء التزاماتهما بانتظام لخدمة"
                        ]
                    },
                
                    "OVERAMBITION": {
                        "causes": [
                            "سعي {hero} لتحقيق قفزة استثنائية دون دراسة المخاطر على {main_char}",
                            "رغبة {hero} في توسيع النطاق بشكل مفاجئ مما حَمَّل {main_char} ما لا يطاق",
                            "اندفاع {hero} نحو أهداف تعجيزية تجاوزت خطة {main_char}"
                        ],
                        "actions": [
                            "{h_decide} {hero} المجازفة بأصول ومكتسبات الفريق دون موافقة {main_char} في",
                            "{h_enter} {hero} في مغامرة غير محسوبة وضع بها مستقبل {main_char} على المحك داخل",
                            "{h_refuse} {hero} التراجع عن سقف طموحه المرتفع رغم تحذيرات {main_char} في"
                        ],
                        "resolutions": [
                            "{h_backpedal} {hero} إلى حدود الواقعية بعد كبوة أولى مجنباً {main_char} خسارة",
                            "{both_reach} {hero} و{main_char} إلى توازن ينظم الطموح بالمقومات المتاحة في",
                            "{both_succeed} {hero} و{main_char} في تحقيق نتائج ممتازة دون تعريض"
                        ]
                    },
                
                    "ETHICAL_DILEMMA": {
                        "causes": [
                            "مواجهة {hero} لمعضلة أخلاقية في طريقة تنفيذ خطة {main_char}",
                            "اصطدام سلوكيات العمل المتبعة بقيم وشرف {hero} أثناء عمله مع {main_char}",
                            "طلب إجراء غير قانوني أو غير أخلاقي أربك حسابات {hero} مع {main_char}"
                        ],
                        "actions": [
                            "{h_refuse} {hero} تطبيق التعليمات اللاحضارية ممتنعاً عن مجاراة {main_char} في",
                            "{h_withdraw} {hero} مستنكراً النهج المتبع {h_leaving} {main_char} في مأزق داخل",
                            "{h_isolate} {hero} موقفه متمسكاً بمبادئه في مواجهة قرارات {main_char} في"
                        ],
                        "resolutions": [
                            "{both_reach} {hero} و{main_char} إلى حل أخلاقي يرضي كافة الأطراف في",
                            "{h_accept} {hero} خطة بديلة تضمن النزاهة دون المساس بمصالح {main_char} في",
                            "{both_restore} {hero} و{main_char} القيم السامية كركيزة أساسية لبناء"
                        ]
                    },
                
                    "FAVORITISM": {
                        "causes": [
                            "شعور {hero} بوجود تحيز من قبل {main_char} لطرف آخر على حسابه",
                            "تصرف {hero} بتحيز أضر بحقوق وقرارات {main_char}",
                            "تمييز غير عادل في توزيع التتقدير أثار غضب {hero} تجاه {main_char}"
                        ],
                        "actions": [
                            "{h_refuse} {hero} الصمت متحدثاً بحدة ومحتجاً على تصرفات {main_char} في",
                            "{h_withdraw} {hero} من التفاعلات المباشرة شعوراً بعدم التقدير من {main_char} داخل",
                            "{h_decide} {hero} تقليص عطائه ليتناسب مع معاملة {main_char} في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من تصحيح سياسة المعاملة وترسيخ المساواة في",
                            "{h_accept} {hero} اعتذار {main_char} عن التمييز غير المقصود في",
                            "{both_restore} {hero} و{main_char} روح الفريق الواحد والقائم على التتقدير في"
                        ]
                    },
                
                    "FACTIONALISM": {
                        "causes": [
                            "نشوب تحزبات داخلية انحاز فيها {hero} لرأي مختلف عن {main_char}",
                            "محاولات أطراف داخلية زرع انشقاق بين {hero} و{main_char}",
                            "تكتل {hero} مع فريق موازٍ مما هدد وضوح الرؤية لدى {main_char}"
                        ],
                        "actions": [
                            "{h_enter} {hero} في صراع معسكرات معلناً تباين موقفه عن {main_char} في",
                            "{h_isolate} {hero} مجموعته عن التنسيق المباشر مع {main_char} داخل",
                            "{h_refuse} {hero} الرضوخ لقرارات التكتل المقابل الذي يمثله {main_char} في"
                        ],
                        "resolutions": [
                            "{both_succeed} {hero} و{main_char} في توحيد الصفوف وإذابة التكتلات داخل",
                            "{h_backpedal} {hero} عن التحزب و{h_agree} مع {main_char} على وحدة الهدف في",
                            "{both_restore} {hero} و{main_char} تماسك الفريق لمواجهة التحديات في"
                        ]
                    },
                
                    "FORGETFULNESS": {
                        "causes": [
                            "سقوط بيانات أو مواعيد حاسمة من ذاكرة {hero} أضر بجدول {main_char}",
                            "سهو {hero} عن إبلاغ {main_char} بتحديثات مصيرية في الوقت المناسب",
                            "غفلة {hero} عن أداء مهمة حيوية أدت لتراكم التبعات على {main_char}"
                        ],
                        "actions": [
                            "{h_fall} {hero} في موقف محرج نتيجة النسيان {h_leaving} {main_char} في مأزق داخل",
                            "{h_lose} {hero} أثر الخطوات المتفق عليها مما أربك حركة {main_char} في",
                            "{h_enter} {hero} في حالة ارتباك محاولاً استدراك ما نسيه أمام {main_char} في"
                        ],
                        "resolutions": [
                            "{h_recover} {hero} البيانات المفقودة مستدركاً النسيان بمساعدة {main_char} في",
                            "{both_manage} {hero} و{main_char} من وضع آليات تذكير تضمن عدم تكرار سهو",
                            "{both_succeed} {hero} و{main_char} في معالجة آثار السهو واستعادة"
                        ]
                    },
                
                    "ABUSE_OF_POWER": {
                        "causes": [
                            "تجاوز {hero} لصلاحياته المحددة والتصرف بفوقية أزعجت {main_char}",
                            "استغلال {hero} لموقعه لفرض آراء فردية على {main_char}",
                            "تعامل {hero} بستعلاء أثار حفيظة {main_char} وهدد العمل"
                        ],
                        "actions": [
                            "{h_decide} {hero} إملاء الأوامر وتهميش دور {main_char} في",
                            "{h_refuse} {hero} تقديم المبررات فارضاً سلطته بحدة على {main_char} داخل",
                            "{h_isolate} {hero} صناعة القرار مستبعداً رأي {main_char} في"
                        ],
                        "resolutions": [
                            "{h_backpedal} {hero} عن أسلوبه التسلطي ملتزماً بالتواضع والتعاون مع {main_char} في",
                            "{both_reach} {hero} و{main_char} إلى تحديد واضح ومستحق للصلاحيات في",
                            "{both_restore} {hero} و{main_char} الممارسة الديمقراطية والتشاركية لضمان"
                        ]
                    },
                
                    "BUREAUCRACY": {
                        "causes": [
                            "إغراق {hero} للعمل بالتفاصيل والشروط المعقدة مما أبطأ خطة {main_char}",
                            "تصلب {hero} في تطبيق اللوائح بشكل جامد عطل مبادرة {main_char}",
                            "تمسك {hero} بإجراءات شكلية معقدة خنقت إبداع {main_char}"
                        ],
                        "actions": [
                            "{h_stop} {hero} المضي قدماً مطبراً اشتراطات تعجيزية بوجه {main_char} في",
                            "{h_refuse} {hero} اختصار الخطوات متمسكاً بالروتين المجهد لـ {main_char} داخل",
                            "{h_withdraw} {hero} خلف الحجج الإجرائية مقيداً حرية تصرف {main_char} في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من تبسيط الإجراءات وإلغاء التعقيدات في",
                            "{h_accept} {hero} التنازل عن الشكليات لصالح مرونة العمل مع {main_char} في",
                            "{both_succeed} {hero} و{main_char} في تسريع وتيرة الإنجاز وتحقيق"
                        ]
                    },
                
                    "RESISTANCE_TO_CHANGE": {
                        "causes": [
                            "مقاومة {hero} الشديدة لتحديث أدوات العمل التي اقترحها {main_char}",
                            "خوف {hero} من النهج الجديد الذي يعتمد عليه {main_char}",
                            "تمسك {hero} بالأدوات القديمة ورفضه مسايرة رؤية {main_char}"
                        ],
                        "actions": [
                            "{h_refuse} {hero} استخدام المنظومة الحديثة مصراً على القديم مع {main_char} في",
                            "{h_withdraw} {hero} من دورات التدريب رافضاً التعلم بالتوازي مع {main_char} داخل",
                            "{h_stop} {hero} عن مجارات التطور مما جعل {main_char} متأخراً في"
                        ],
                        "resolutions": [
                            "{h_accept} {hero} التدرب والتكيف مع المنظومة الحديثة بدعم من {main_char} في",
                            "{both_overcome} {hero} و{main_char} فجوة التطوير وانتقلا بنجاح إلى",
                            "{both_succeed} {hero} و{main_char} في جني ثمار التحديث والتطوير داخل"
                        ]
                    },
                
                    "UNBALANCED_SACRIFICE": {
                        "causes": [
                            "تقديم {hero} لتضحيات كبيرة دون العثور على تقدير مناسب من {main_char}",
                            "شعور {hero} بأن {main_char} يستغل اندفاعه وتضحياته المستمرة",
                            "استنزاف قدرات {hero} في سد ثغرات {main_char} دون مقابل معنوي"
                        ],
                        "actions": [
                            "{h_stop} {hero} عن تقديم أي تضحيات إضافية معلناً اكتفاءه أمام {main_char} في",
                            "{h_withdraw} {hero} بصمت شعوراً بالخذلان تجاه {main_char} داخل",
                            "{h_refuse} {hero} القيام بالمهام الاستثنائية لصالح {main_char} في"
                        ],
                        "resolutions": [
                            "{h_receive} {hero} التقدير والتكريم المستحق من {main_char} و{h_return_to} إلى",
                            "{both_reach} {hero} و{main_char} إلى موازنة تضمن العدالة والتكافؤ في",
                            "{both_restore} {hero} و{main_char} التعاون القائم على التقدير المتبادل لـ"
                        ]
                    },
                
                    "FALSE_OPTIMISM": {
                        "causes": [
                            "بناء {hero} لتوقعات خيالية غير واقعية أربكت خطط {main_char}",
                            "تفاءل {hero} المفرط الذي حجب عنه رؤية العقبات الحقيقية أمام {main_char}",
                            "وعود زهرية قدمها {hero} لـ {main_char} اصطدمت بخرسانة الواقع"
                        ],
                        "actions": [
                            "{h_fall} {hero} في صدمة الواقع {h_leaving} {main_char} يواجه العواقب في",
                            "{h_lose} {hero} الحماس فجأة بعد انكشاف حقيقة التحديات أمام {main_char} داخل",
                            "{h_enter} {hero} في حالة إحباط نتيجة الخيبة التي تسبب بها لـ {main_char} في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من بناء خطة واقعية قائمة على المعطيات في",
                            "{h_recover} {hero} اتزانه متبنياً نظرة موضوعية بمساعدة {main_char} في",
                            "{both_succeed} {hero} و{main_char} في تحويل الأهداف إلى نتائج ملموسة لـ"
                        ]
                    },
                
                    "SPONSOR_PRESSURE": {
                        "causes": [
                            "شروط قاسية فرضتها جهات تمويلية أربكت العمل بين {hero} و{main_char}",
                            "ضغط الممولين على {hero} لاتخاذ قرارات لا ترضي {main_char}",
                            "تهديد الراعي بسحب الدعم مما وضع {hero} و{main_char} في مأزق"
                        ],
                        "actions": [
                            "{h_decide} {hero} الخضوع لرغبة الراعي مجبراً {main_char} على التنازل في",
                            "{h_withdraw} {hero} من التمويل محاولاً البحث عن بدائل دون {main_char} داخل",
                            "{h_refuse} {hero} الاستمرار في ظل الشروط المائة لمساندة {main_char} في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من التفاوض مع الجهة المانحة وتحسين شروط",
                            "{both_succeed} {hero} و{main_char} في تأمين تمويل مستقل أنقذ",
                            "{h_reach} {hero} و{main_char} إلى حل وسط أطفأ شروط الضغط في"
                        ]
                    },
                
                    "COMPETITOR_INFILTRATION": {
                        "causes": [
                            "حركات مشبوهة لمنافسين حاولوا استدراج {hero} لترك {main_char}",
                            "تقديم اغراءات خارجية لـ {hero} للتخلي عن مشروعه مع {main_char}",
                            "محاولة المنافسين خلق فتنة مباشرة بين {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_enter} {hero} في مفاوضات سرية مع المنافسين ملهياً {main_char} في",
                            "{h_distract} اهتمامه بعروض المنافسين وترك العمل المشترك مع {main_char} داخل",
                            "{h_withdraw} {hero} تدريجياً نحو معسكر المنافسين مسبباً صدمة لـ {main_char} في"
                        ],
                        "resolutions": [
                            "{h_backpedal} {hero} عن إغراءات المنافسين متمسكاً بولائه لـ {main_char} في",
                            "{both_succeed} {hero} و{main_char} في إفشال مخطط المنافسين وحماية",
                            "{both_restore} {hero} و{main_char} قوة تحالفهما في وجه التحديات الخارجية لـ"
                        ]
                    },
                
                    "RIGIDITY": {
                        "causes": [
                            "رفض {hero} تعديل الخطة رغم تغير الظروف الميدانية مع {main_char}",
                            "جمود التفكير لدى {hero} ومطالبته لـ {main_char} بالالتزام الحرفي الميت",
                            "تصلب {hero} في التعاطي مع المستجدات الطارئة التي واجهت {main_char}"
                        ],
                        "actions": [
                            "{h_refuse} {hero} المبادرة بأي مرونة معطلاً حركة {main_char} في",
                            "{h_stop} {hero} عن تنفيذ التعديلات المقترحة من {main_char} داخل",
                            "{h_isolate} {hero} الخطط عن التغيير مجبراً {main_char} على النمطية في"
                        ],
                        "resolutions": [
                            "{both_reach} {hero} و{main_char} إلى استراتيجية مرنة تتكيف مع التغيرات في",
                            "{h_accept} {hero} أهمية التحديث المستمر وملاءمة خطط {main_char} في",
                            "{both_succeed} {hero} و{main_char} في تجاوز الجمود وتحقيق نتائج أفضل بـ"
                        ]
                    },
                
                    "EMOTIONAL_IMPULSE": {
                        "causes": [
                            "تصرف {hero} بدوافع عاطفية محضة أربكت الحسابات العقلانية لـ {main_char}",
                            "غضب فجائي تملك {hero} تسبب في إفساد جزء من عمل {main_char}",
                            "حساسية مفرطة أبداها {hero} تجاه مواقف عادية الصدور من {main_char}"
                        ],
                        "actions": [
                            "{h_fall} {hero} تحت غشاوة الانفعال متخذاً قراراً متسرعاً أضر بـ {main_char} في",
                            "{h_withdraw} {hero} بدافع الزعل والاندفاع {h_leaving} {main_char} في حيرة داخل",
                            "{h_decide} {hero} القطيعة الانفعالية دون تدبر العواقب مع {main_char} في"
                        ],
                        "resolutions": [
                            "{h_recover} {hero} هدوءه وعقلانيته واعتذر لـ {main_char} مصلحاً",
                            "{both_overcome} {hero} و{main_char} ثورة المشاعر عبر الحوار الهادئ في",
                            "{both_restore} {hero} و{main_char} التوازن العاطفي والعقلاني لتوجيه"
                        ]
                    },
                
                    "DEADLINE_PRESSURE": {
                        "causes": [
                            "اقتراب موعد التسليم النهائي مما وضع {hero} و{main_char} تحت ضغط هائل",
                            "ضيق الوقت المتبقي لإنجاز خطة {hero} المساندة لـ {main_char}",
                            "مهلة زمنية حرجة فرضت توتراً حاداً في التعامل بين {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_lose} {hero} تركيزه بسبب الشد العصبي محبطاً جهود {main_char} في",
                            "{h_stop} {hero} عن العمل نتيجة الشعور باستحالة الإنجاز مع {main_char} داخل",
                            "{h_enter} {hero} في حالة ارتباك متسارع أضاعت الوقت على {main_char} في"
                        ],
                        "resolutions": [
                            "{both_succeed} {hero} و{main_char} في تكثيف الجهود واستغلال كل ثانية لإنجاز",
                            "{both_manage} {hero} و{main_char} من إنهاء المطلوب قبل الموعد النهائي في",
                            "{h_recover} {hero} ثباته ونجح في قيادة السباق الزمني مع {main_char} لـ"
                        ]
                    },
                
                    "LOGISTICAL_FAILURE": {
                        "causes": [
                            "تعطل وسائل النقل أو الإمداد التي ينظمها {hero} لصالح {main_char}",
                            "فشل وصول التجهيزات الأساسية التي وعد بها {hero} لـ {main_char}",
                            "خلل في خطط الشحن والتوزيع التي يعتمد عليها {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_lose} {hero} القدرة على إيصال الموارد في الموعد المكتوب لـ {main_char} في",
                            "{h_withdraw} {hero} إلى مركز الإمداد محاولاً البحث عن حلول دون {main_char} داخل",
                            "{h_enter} {hero} في حالة شلل لوجستي عطل حركة {main_char} في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من فتح خطوط إمداد بديلة أمنت",
                            "{h_overcome} {hero} الخلل اللوجستي وأوصل التجهيزات لـ {main_char} في",
                            "{both_succeed} {hero} و{main_char} في إعادة هيكلة الدعم والمشونات لـ"
                        ]
                    },
                
                    "CULTURAL_GAP": {
                        "causes": [
                            "اختلاف الخلفية الثقافية أو الفكرية لـ {hero} عن {main_char} مما أحدث سوء فهم",
                            "تباين المصطلحات والمفاهيم المستخدمة بين {hero} و{main_char}",
                            "تفسير خاطئ لسلوكيات {hero} بسبب المرجعية الفكرية المغايرة لـ {main_char}"
                        ],
                        "actions": [
                            "{h_refuse} {hero} النهج المتبع نظراً لتعارضه مع مفاهيمه أمام {main_char} في",
                            "{h_isolate} {hero} أفكاره مفضلاً عدم النقاش العقائدي/الفكري مع {main_char} داخل",
                            "{h_withdraw} {hero} شعوراً بعدم الانسجام الثقافي مع {main_char} في"
                        ],
                        "resolutions": [
                            "{both_reach} {hero} و{main_char} إلى فهم مشترك واحترام التنوع في",
                            "{h_accept} {hero} تقبل الاختلاف والاستفادة من النظرة المغايرة لـ {main_char} في",
                            "{both_succeed} {hero} و{main_char} في بناء بيئة عمل تستوعب الجميع لـ"
                        ]
                    },
                
                    "UNREALISTIC_EXPECTATIONS": {
                        "causes": [
                            "مطالبة {main_char} لـ {hero} بمخرجات تتجاوز حدوده",
                            "انتظار {hero} لنتائج سحرية ومباشرة من {main_char} دون مقدمات",
                            "وضع معايير تقييم خيالية تسببت في إحباط {hero} أمام {main_char}"
                        ],
                        "actions": [
                            "{h_stop} {hero} عن الاستمرار شعوراً بظلم المعايير المفرطة من {main_char} في",
                            "{h_refuse} {hero} الاستجابة للمطالب غير المنطقية المعروضة من {main_char} داخل",
                            "{h_withdraw} {hero} يائساً من القدرة على إرضاء توقعات {main_char} في"
                        ],
                        "resolutions": [
                            "{both_reach} {hero} و{main_char} إلى إعادة ضبط المعايير لتصبح منطقية في",
                            "{h_accept} {hero} التحدي بعد تعديل التوقعات الشاطحة من قبل {main_char} في",
                            "{both_succeed} {hero} و{main_char} في تحقيق أهداف مرحلية واقعية لـ"
                        ]
                    },
                
                    "FORCE_MAJEURE": {
                        "causes": [
                            "وقوع حادث بيئي أو طبيعي خارج عن الإرادة شل حركة {hero} و{main_char}",
                            "تغيب إجباري لـ {hero} نتيجة ظروف قاهرة غير متوقعة أثرت على {main_char}",
                            "أزمة عامة أدت إلى تجميد النشاط القائم بين {hero} و{main_char}"
                        ],
                        "actions": [
                            "{h_stop} {hero} قسراً عن العمل مفصُولاً عن قنوات التواصل مع {main_char} في",
                            "{h_lose} {hero} القدرة على الحركة والتأثير مجبراً على التراجع أمام {main_char} داخل",
                            "{h_isolate} {hero} في موقعه متأثراً بالظروف القاهرة بعيداً عن {main_char} في"
                        ],
                        "resolutions": [
                            "{both_manage} {hero} و{main_char} من التكيف مع القوة القاهرة وابتكار سبل لـ",
                            "{both_overcome} {hero} و{main_char} آثار الظرف القاهر وأعادا تجميع",
                            "{both_succeed} {hero} و{main_char} في الخروج بأقل الخسائر وحماية"
                        ]
                    },
                
                    "HARSH_FEEDBACK": {
                        "causes": [
                            "توجيه {main_char} لنقد قاسم ومحبط لأداء {hero}",
                            "انتقاد {hero} لأسلوب {main_char} بطريقة جارحة وغير بناءة",
                            "تلقي {hero} لتقييم سلبي علني أضر بكرامته أمام {main_char}"
                        ],
                        "actions": [
                            "{h_withdraw} {hero} مجروح الكبرياء والكرامة ورافضاً الحديث مع {main_char} في",
                            "{h_refuse} {hero} استقبال أي توجيهات جديدة من {main_char} داخل",
                            "{h_enter} {hero} في حالة صمت وااحتجاج سلبي ضد معاملة {main_char} في"
                        ],
                        "resolutions": [
                            "{h_accept} {hero} النقد بعد تحسين أسلوب العرض وتوضيح النوايا من {main_char} في",
                            "{both_restore} {hero} و{main_char} ثقافة التقييم البناء والاحترام المتبادل في",
                            "{both_succeed} {hero} و{main_char} في تجاوز الحساسيات الفردية لبناء"
                        ]
                    }
                }

    @staticmethod
    def extract_story_characters(nodes):
        hero = None
        main_char = None

        for node in nodes:
            label = node.get("label", "").strip()
            role = node.get("role", "").strip()

            if role in ["البطل", "البداية"]:
                hero = label
            elif role in ["رئيسية", "الخاتمة", "خطوة"] and not main_char:
                main_char = label

        if not hero and nodes:
            hero = nodes[0].get("label", "").strip()
        if not main_char and len(nodes) > 1:
            main_char = nodes[1].get("label", "").strip()

        return hero, main_char

    @staticmethod
    def get_all_conflict_edges(json_data):
        conflicts = []

        if "broken_edges" in json_data:
            conflicts.extend(json_data["broken_edges"])
        elif "conflict_edges" in json_data:
            conflicts.extend(json_data["conflict_edges"])
        elif "conflicts" in json_data:
            for c in json_data["conflicts"]:
                conflicts.extend(c.get("edges", []))

        for edge in conflicts:
            if isinstance(edge.get("source"), str):
                edge["source"] = edge["source"].strip()
            if isinstance(edge.get("target"), str):
                edge["target"] = edge["target"].strip()
            if isinstance(edge.get("relation"), str):
                edge["relation"] = edge["relation"].strip()

        return conflicts

    def _get_words(self, is_hero_female: bool, is_main_female: bool) -> dict:
        return {
            "h_decide": "قررت" if is_hero_female else "قرر",
            "h_withdraw": "انسحبت" if is_hero_female else "انسحب",
            "h_leaving": "تاركةً" if is_hero_female else "تاركاً",
            "h_refuse": "رفضت" if is_hero_female else "رفض",
            "h_backpedal": "تراجعت" if is_hero_female else "تراجع",
            "h_agree": "ووافقت" if is_hero_female else "ووافق",
            "h_accept": "قبلت" if is_hero_female else "قبل",
            "h_reach": "توصلت" if is_hero_female else "توصل",
            "h_stop": "توقفت" if is_hero_female else "توقف",
            "h_fall": "سقطت" if is_hero_female else "سقط",
            "h_tired": "منهكةً" if is_hero_female else "منهكاً",
            "h_enter": "دخلت" if is_hero_female else "دخل",
            "h_recover": "استعادت" if is_hero_female else "استعاد",
            "h_return_to": "لتعود" if is_hero_female else "ليعود",
            "h_receive": "تلقّت" if is_hero_female else "تلقى",
            "h_resume": "لتستأنف" if is_hero_female else "ليستأنف",
            "h_overcome": "تجاوزت" if is_hero_female else "تجاوز",
            "h_isolate": "عُزلت" if is_hero_female else "عُزل",
            "h_distract": "تشتت" if is_hero_female else "تشتت",
            "h_lose": "فقدت" if is_hero_female else "فقد",
            "m_manage": "تدير" if is_main_female else "يدير",
            "both_manage": "تمكنتا" if (is_hero_female and is_main_female) else "تمكّنا",
            "both_return": "وعادتا" if (is_hero_female and is_main_female) else "وعادا",
            "both_overcome": "تغلبت" if is_hero_female else "تغلب",
            "both_restore": "واستعادتا" if (is_hero_female and is_main_female) else "واستعادا",
            "both_succeed": "نجحت" if (is_hero_female and is_main_female) else "نجح",
        }

    def generate_arc(self, hero: str, main_char: str, target: str, place: str,
                     is_hero_female: bool = False, is_main_female: bool = False) -> Tuple[str, str]:
        category_name = self.rng.choice(list(self.dramatic_catalysts.keys()))
        category = self.dramatic_catalysts[category_name]

        hero_def = definite_label(hero)
        main_char_def = definite_label(main_char)
        target_def = definite_label(target)
        place_text = place if place and place != "غير محدد" else "ذلك المكان"

        gender_words = self._get_words(is_hero_female, is_main_female)

        fmt_context = {
            "hero": hero_def,
            "main_char": main_char_def,
            **gender_words
        }

        cause = self.rng.choice(category["causes"]).format(**fmt_context)
        action = self.rng.choice(category["actions"]).format(**fmt_context)
        resolution = self.rng.choice(category["resolutions"]).format(**fmt_context)

        plot_text = f"إثر {cause}، {action} {place_text} مما أثر على {target_def}"
        solution_text = f"وفي نهاية المطاف، {resolution} {target_def}"

        return plot_text, solution_text


OPENERS = ["كان يا ما كان، في قديم الزمان...", "كان يا ما كان،يحكى أنه", "يُروى أنه في قديم الزمان"]
TIME_PLACE = ["في زمنٍ {time}، وفي مكانٍ يُدعى {place}،"]
TIME_PLACE_FALLBACK = ["في زمنٍ غابر، وفي مكانٍ يعجّ بالحياة الخفية،"]
PLACE_ONLY_TEMPLATES = ["وفي مكانٍ يُدعى {place}،"]
TIME_ONLY_TEMPLATES = ["في زمن {time}،"]
CHARACTER_INTRO = ["عاش في هذا المكان شخصيات عدة، أبرزها: {chars}."]
PEACEFUL_LIFE = ["وعاشت الأمور بسلامٍ وهدوء حيث"]
TURNING_POINT = ["وفجأة..."]
RETURN_TO_NORMAL = ["فعادت الأحوال كسابق عهدها حيث"]
ENDING_PHRASES = ["وبذلك عادت المياه لمجاريها حيث"]
CLOSING_TAGLINES = ["وعادت الأمور كسابق عهدها."]
MIDDLE_SEPARATORS = ["، و"]
MIDDLE_SEPARATORS_NEUTRAL = ["، و"]
LAST_SEPARATORS = ["، إضافة إلى أنّ "]
LAST_SEPARATORS_NEUTRAL = ["، إضافة إلى "]
LAST_SEPARATORS_SHORT = ["، إضافة إلى أنّ "]
LAST_SEPARATORS_SHORT_NEUTRAL = ["، إضافة إلى "]


def edge_literal_sentence(source: str, relation: str, target: str, is_conflict_stage: bool = False) -> str:
    src_def = definite_label(source)
    tgt_def = definite_label(target)
    rel_clean = clean(relation)

    if is_conflict_stage:
        if src_def.startswith("عدم") or src_def.startswith("لا"):
            return f"{src_def} يمنع عمل {tgt_def}"
        elif "لا" in rel_clean or "عدم" in rel_clean:
            return f"{src_def} {rel_clean.replace('لا ', '').replace('عدم ', '')} {tgt_def}"
        else:
            return f"{src_def} يواجه صعوبة حيث {rel_clean} {tgt_def}"
    else:
        if rel_clean.startswith("بواسطة"):
            return f"يتحقق {src_def} {rel_clean} {tgt_def}"
        elif rel_clean.startswith("نوعه"):
            return f"يكون {src_def} من نوع {tgt_def}"
        else:
            return f"{src_def} {rel_clean} {tgt_def}"


def get_story_elements_pool(story_elements: Optional[dict]) -> dict:
    return (story_elements or {}).get("العناصر", {}) or {}


def get_hero_label(story_elements: Optional[dict], sna_graph: Optional[dict] = None) -> Optional[str]:
    pool = get_story_elements_pool(story_elements)
    heroes = pool.get("البطل", [])
    if heroes:
        return clean(heroes[0])

    if sna_graph and "nodes" in sna_graph:
        hero, _ = DramaticEngine.extract_story_characters(sna_graph["nodes"])
        return hero
    return None


class StoryBuilder:
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.dramatic_engine = DramaticEngine(self.rng)
        self._cached_solution_text: Optional[str] = None
        self._antonym_mismatch: bool = False
        self._conflict_hero: Optional[str] = None
        self._conflict_main_char: Optional[str] = None
        self._conflict_place: str = ""
        self._conflict_sna_graph: Optional[dict] = None
        self._conflict_filtered_graph: Optional[dict] = None

        self.banks: Dict[str, PhraseBank] = {
            "openers": PhraseBank(OPENERS, self.rng),
            "time_place": PhraseBank(TIME_PLACE, self.rng),
            "time_place_fallback": PhraseBank(TIME_PLACE_FALLBACK, self.rng),
            "place_only": PhraseBank(PLACE_ONLY_TEMPLATES, self.rng),
            "time_only": PhraseBank(TIME_ONLY_TEMPLATES, self.rng),
            "character_intro": PhraseBank(CHARACTER_INTRO, self.rng),
            "peaceful_life": PhraseBank(PEACEFUL_LIFE, self.rng),
            "turning_point": PhraseBank(TURNING_POINT, self.rng),
            "return_to_normal": PhraseBank(RETURN_TO_NORMAL, self.rng),
            "ending": PhraseBank(ENDING_PHRASES, self.rng),
            "closing_tagline": PhraseBank(CLOSING_TAGLINES, self.rng),
            "middle_separator": PhraseBank(MIDDLE_SEPARATORS, self.rng),
            "middle_separator_neutral": PhraseBank(MIDDLE_SEPARATORS_NEUTRAL, self.rng),
            "last_separator": PhraseBank(LAST_SEPARATORS, self.rng),
            "last_separator_neutral": PhraseBank(LAST_SEPARATORS_NEUTRAL, self.rng),
            "last_separator_short": PhraseBank(LAST_SEPARATORS_SHORT, self.rng),
            "last_separator_short_neutral": PhraseBank(LAST_SEPARATORS_SHORT_NEUTRAL, self.rng),
        }

    def join_relations(self, sentences: List[str]) -> str:
        cleaned = [s.strip() for s in sentences if s.strip()]
        if not cleaned:
            return ""
        if len(cleaned) == 1:
            return cleaned[0] + "."
        body = cleaned[0]
        for s in cleaned[1:-1]:
            sep = "middle_separator_neutral" if s.startswith("عدم") else "middle_separator"
            body += self.banks[sep].get() + s
        last = cleaned[-1]
        if len(cleaned) < 3:
            sep_last = "last_separator_short_neutral" if last.startswith("عدم") else "last_separator_short"
        else:
            sep_last = "last_separator_neutral" if last.startswith("عدم") else "last_separator"
        body += self.banks[sep_last].get() + last
        return body + "."

    def rule_intro(self, sna_graph: dict, story_elements: Optional[dict] = None) -> str:
        elements_pool = get_story_elements_pool(story_elements)
        hero = get_hero_label(story_elements, sna_graph)
        mains_pool = [clean(x) for x in elements_pool.get("رئيسية", []) if clean(x) != hero]

        if hero:
            chosen_mains = self.rng.sample(mains_pool, 2) if len(mains_pool) >= 2 else mains_pool
            chars_raw = [hero] + chosen_mains
        else:
            nodes = sna_graph.get("nodes", [])
            chars_raw = [clean(n["label"]) for n in nodes[:3]]

        chosen = [definite_label(c) for c in chars_raw if c]
        opener = self.banks["openers"].get()

        if story_elements:
            place_raw = clean(story_elements.get("المكان") or "")
            time_raw = clean(story_elements.get("الزمان") or "غير محدد")
            place_known = bool(place_raw) and place_raw != "غير محدد"
            time_known = bool(time_raw) and time_raw != "غير محدد"

            if time_known and place_known:
                tp = self.banks["time_place"].get().format(time=time_raw, place=place_raw)
            elif place_known:
                tp = self.banks["place_only"].get().format(place=place_raw)
            elif time_known:
                tp = self.banks["time_only"].get().format(time=time_raw)
            else:
                tp = self.banks["time_place_fallback"].get()
        else:
            tp = self.banks["time_place_fallback"].get()

        parts = [opener, tp]
        if chosen:
            parts.append(self.banks["character_intro"].get().format(chars="، ".join(chosen)))

        return " ".join(p for p in parts if p)

    def rule_peaceful_life(self, filtered_graph: dict) -> str:
        edges = filtered_graph.get("edges", [])
        chosen = self.rng.sample(edges, 2) if len(edges) > 2 else edges
        sentences = [edge_literal_sentence(e["source"], e["relation"], e["target"]) for e in chosen]
        detail = self.join_relations(sentences)
        opener = self.banks["peaceful_life"].get()
        return f"{opener} {detail}" if detail else opener

    def rule_turning_point(self) -> str:
        return self.banks["turning_point"].get()

    @staticmethod
    def _negation_words(is_source_female: bool) -> dict:
        return {
            "no_longer": "لم تعد" if is_source_female else "لم يعد",
            "became": "باتت" if is_source_female else "بات",
            "face": "تواجه" if is_source_female else "يواجه",
            "lost": "فقدت" if is_source_female else "فقد",
            "stopped": "توقفت" if is_source_female else "توقف",
            "regained": "استعادت" if is_source_female else "استعاد",
            "returned": "عادت" if is_source_female else "عاد",
            "her_his": "ها" if is_source_female else "ه",
        }

    def _build_negated_problem(self, source_def: str, relation: str, target_def: str, w: dict) -> str:
        templates = [
            f"{w['no_longer']} {source_def} {relation} {target_def}",
            f"{w['became']} {source_def} {w['face']} صعوبة بالغة في التعامل مع {target_def}",
            f"{w['lost']} {source_def} القدرة على أن {relation} {target_def}",
            f"{w['stopped']} {source_def} عن أن {relation} {target_def}",
        ]
        return self.rng.choice(templates)

    def rule_plot_twist(self, antonym_graph: dict, sna_graph: dict, filtered_graph: dict,
                        story_elements: Optional[dict] = None) -> str:
        hero = get_hero_label(story_elements, filtered_graph) or get_hero_label(story_elements, sna_graph)
        nodes_for_pair = (filtered_graph or {}).get("nodes") or sna_graph.get("nodes", [])

        if not hero:
            hero, main_char = DramaticEngine.extract_story_characters(nodes_for_pair)
        else:
            _, main_char = DramaticEngine.extract_story_characters(nodes_for_pair)

        if not main_char or main_char == hero:
            main_char = "الرفيق"

        is_hero_female = is_female_name(hero)
        is_main_female = is_female_name(main_char)

        place = clean((story_elements or {}).get("المكان", ""))

        conflicts = DramaticEngine.get_all_conflict_edges(antonym_graph) if antonym_graph else []
        hero_edges = [e for e in conflicts if e.get("source") == hero or e.get("original_source") == hero]

        filtered_edges = (filtered_graph or {}).get("edges", [])

        mismatch_or_missing = not antonym_graph or not filtered_edges or (bool(conflicts) and not hero_edges)

        self._antonym_mismatch = mismatch_or_missing
        self._conflict_hero = hero
        self._conflict_main_char = main_char
        self._conflict_place = place
        self._conflict_sna_graph = sna_graph
        self._conflict_filtered_graph = filtered_graph

        if mismatch_or_missing:
            target_node = (sna_graph.get("edges", [{}])[0]).get("target", "الهدف")
            catalysts_plot, solution_text = self.dramatic_engine.generate_arc(
                hero=hero,
                main_char=main_char,
                target=target_node,
                place=place,
                is_hero_female=is_hero_female,
                is_main_female=is_main_female
            )
            plot_text = catalysts_plot
        else:
            target = hero_edges[0]["target"] if hero_edges else (conflicts[0]["target"] if conflicts else "البيئة المحيطة")
            plot_text, solution_text = self.dramatic_engine.generate_arc(
                hero=hero,
                main_char=main_char,
                target=target,
                place=place,
                is_hero_female=is_hero_female,
                is_main_female=is_main_female
            )

        self._cached_solution_text = solution_text

        return f"{plot_text}، حيث"

    def _city_state_from_fallback_graph(self) -> str:
        sna_graph = self._conflict_sna_graph or {}
        hero = self._conflict_hero
        edges = sna_graph.get("edges", [])
        hero_edges = [e for e in edges if e.get("source") == hero]
        pool = hero_edges if hero_edges else edges
        if not pool:
            return ""

        selected_edges = pool[:4]

        causal_sentences = []
        for e in selected_edges:
            src_def = definite_label(e.get("source", hero))
            tgt_def = definite_label(e.get("target", ""))
            relation = clean(e.get("relation", ""))
            w = self._negation_words(is_female_name(e.get("source", hero)))
            causal_sentences.append(self._build_negated_problem(src_def, relation, tgt_def, w))

        if len(causal_sentences) == 1:
            return causal_sentences[0] + "."

        causal_connectors = [
            "، مما زاد الطين بلة أنّ ",
            "، الأمر الذي أدى بدوره إلى أنّ ",
            "، ونتيجة لهذا الخلل فإنّ ",
            "، ما ترتب عليه أنّ "
        ]

        result = causal_sentences[0]
        for i, s in enumerate(causal_sentences[1:]):
            connector = causal_connectors[i % len(causal_connectors)]
            result += connector + s

        return result + "."

    def rule_city_state_after_incident(self, antonym_graph: dict) -> str:
        if self._antonym_mismatch:
            return self._city_state_from_fallback_graph()

        edges = DramaticEngine.get_all_conflict_edges(antonym_graph)
        if not edges:
            return self._city_state_from_fallback_graph()

        causal_sentences = [edge_literal_sentence(e["source"], e["relation"], e["target"], is_conflict_stage=True) for e in edges]

        if len(causal_sentences) == 1:
            return causal_sentences[0] + "."

        causal_connectors = [
            "، مما زاد الطين بلة أنّ ",
            "، الأمر الذي أدى بدوره إلى أنّ ",
            "، ونتيجة لهذا الخلل فإنّ ",
            "، ما ترتب عليه أنّ "
        ]

        result = causal_sentences[0]
        for i, s in enumerate(causal_sentences[1:]):
            connector = causal_connectors[i % len(causal_connectors)]
            if connector.endswith("أنّ ") and s.startswith("عدم"):
                connector = connector.replace("أنّ ", "توقف ")
            result += connector + s

        return result + "."

    def rule_uprising(self) -> str:
        return ""

    def rule_reaction(self) -> str:
        return ""

    def rule_hero_return(self) -> str:
        if self._cached_solution_text:
            return self._cached_solution_text + "."
        return "وعاد كل شيء إلى نصابه بفضل التدخل الحاسم."

    def rule_return_to_normal(self, filtered_graph: dict) -> str:
        opener = self.banks["return_to_normal"].get()
        edges = filtered_graph.get("edges", [])
        sentences = [edge_literal_sentence(e["source"], e["relation"], e["target"]) for e in edges]
        detail = self.join_relations(sentences)
        return f"{opener} {detail}" if detail else opener

    def rule_ending(self, filtered_graph: dict) -> str:
        opener = self.banks["ending"].get()
        edges = filtered_graph.get("edges", [])
        chosen = self.rng.sample(edges, 2) if len(edges) > 2 else edges
        sentences = [edge_literal_sentence(e["source"], e["relation"], e["target"]) for e in chosen]
        detail = self.join_relations(sentences)
        return f"{opener} {detail}" if detail else opener

    def rule_closing_tagline(self) -> str:
        return self.banks["closing_tagline"].get()


def generate_story(sna_graph_path: str,
                   antonym_plot_path: str,
                   sna_graph_filtered_path: str,
                   story_elements_path: Optional[str] = None,
                   seed: Optional[int] = None) -> str:
    sna_graph = load_json(sna_graph_path)
    antonym_graph = load_antonym_graph(antonym_plot_path)
    filtered_graph = load_json(sna_graph_filtered_path)

    story_elements = None
    if story_elements_path and os.path.exists(story_elements_path):
        story_elements = load_json(story_elements_path)

    builder = StoryBuilder(seed=seed)

    sections = [
        builder.rule_intro(sna_graph, story_elements=story_elements),
        builder.rule_peaceful_life(filtered_graph),
        builder.rule_turning_point(),
        builder.rule_plot_twist(antonym_graph, sna_graph, filtered_graph, story_elements),
        builder.rule_city_state_after_incident(antonym_graph),
        builder.rule_uprising(),
        builder.rule_reaction(),
        builder.rule_hero_return(),
        builder.rule_return_to_normal(filtered_graph),
        builder.rule_ending(filtered_graph),
        builder.rule_closing_tagline(),
    ]

    return "\n\n".join(s for s in sections if s.strip())


if __name__ == "__main__":
    story_text = generate_story(
        sna_graph_path="../sna/results/sna_plot_graph.json",
        antonym_plot_path="../sna/results/antonym_plot.json",
        sna_graph_filtered_path="../sna/results/sna_plot_graph_filtered.json",
        story_elements_path="../sna/results/story_elements.json",
        seed=None,
    )
    print(story_text)

    with open("generated_story.txt", "w", encoding="utf-8") as f:
        f.write(story_text)

import os
from pathlib import Path
import sys

from google import genai


sys.stdout.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")


def refine_story_with_llm(story_text: str, api_key: str) -> str:
    from google import genai
    from google.genai import types

    api_key = api_key.strip().strip('"').strip("'")

    client = genai.Client(api_key=api_key)

    system_instruction = """
أنت محرر أدبي محترف ومختص في صياغة القصص والنصوص الدرامية.

مهمتك هي تحسين الصياغة اللغوية والربط البلاغي للقصة المقدمة إليك.

الشروط الإلزامية:

1. حافظ على جميع الأحداث كما هي.
2. حافظ على جميع أسماء الشخصيات.
3. حافظ على جميع العلاقات بين الشخصيات.
4. لا تحذف أي حدث.
5. لا تضف أي أحداث جديدة.
6. لا تضف أي شخصيات جديدة.
7. لا تغيّر تسلسل الأحداث.
8. لا تغيّر معنى القصة.
9. حسّن تدفق الجمل والانتقال بين الفقرات.
10. صحح الأخطاء الإملائية والنحوية.
11. اجعل الأسلوب أكثر انسيابية وجاذبية أدبيًا.
12. أعد القصة المحسنة فقط دون مقدمة أو شرح أو تعليقات.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=story_text,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        ),
    )

    if not response.text:
        raise Exception("Gemini أعاد استجابة بدون نص.")

    return response.text


if __name__ == "__main__":

    # هون حطيت API Gemini من التيرمينال بالتعليمة:
    """
    $env:GEMINI_API_KEY="YOUR_NEW_API_KEY"
    """
    MY_API_KEY = os.environ["GEMINI_API_KEY"]

    base_dir = Path(__file__).resolve().parent
    input_file_path = base_dir / "generated_story.txt"
    output_file_path = base_dir / "final_story.txt"

    try:

        with open(
            input_file_path,
            "r",
            encoding="utf-8"
        ) as f:
            original_story = f.read()

        print(
            "تمت قراءة القصة بنجاح. "
            "جاري تحسين النص بواسطة LLM...\n"
        )

        refined_story = refine_story_with_llm(
            original_story,
            MY_API_KEY
        )

        with open(
            output_file_path,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(refined_story)

        print(
            "تم حفظ القصة المحسنة بنجاح في:"
        )

        print(output_file_path)

    except FileNotFoundError:

        print(
            "خطأ: لم يتم العثور على الملف في المسار:"
        )

        print(input_file_path)

    except Exception as e:

        print(
            f"حدث خطأ أثناء معالجة القصة: {e}"
        )