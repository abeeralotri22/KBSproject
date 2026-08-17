import json
import os
import subprocess
import sys
import importlib.util

import requests

from django.conf import settings
from django.db import transaction

from .models import Lesson, StoryHistory


NLP_API_URL = "https://judy4444-text2tale-nlp.hf.space/generate_graph"


def generate_story_for_lesson(user, lesson_id):
    """
    توليد قصة للدرس عبر الـ NLP + Knowledge Graph + SNA + creatingStory.

    Pipeline:

    1. جلب الدرس.
    2. إرسال محتوى الدرس إلى NLP API.
    3. حفظ graph الناتج.
    4. تشغيل createandupdategraph.py.
    5. تشغيل filter_graph.py.
    6. تشغيل خطوات SNA.
    7. تشغيل antonym.py.
    8. قراءة story_elements.json.
    9. تشغيل creatingStory.py.
    10. تحسين القصة بواسطة Gemini.
    11. حفظ القصة في StoryHistory.

    ملاحظة مهمة:
    antonym_plot.json ليس ملفًا إلزاميًا.
    بعض أنواع القصص، مثل:
        archetype = chain
        chain_subtype = sequence

    قد لا تنتج antonym_plot.json.
    لذلك إذا لم يوجد الملف، نرسل None إلى creatingStory.
    """

    # ============================================================
    # 1. جلب الدرس
    # ============================================================

    try:
        lesson = (
            Lesson.objects
            .select_related("subject")
            .get(
                id=lesson_id,
                user=user
            )
        )

    except Lesson.DoesNotExist:
        return {
            "success": False,
            "message": "الدرس غير موجود أو لا تملك صلاحية الوصول إليه."
        }

    if not lesson.content or not lesson.content.strip():
        return {
            "success": False,
            "message": "محتوى الدرس فارغ."
        }

    # ============================================================
    # 2. الاتصال بـ NLP
    # ============================================================

    payload = {
        "text": lesson.content
    }

    try:

        print("\n" + "=" * 70)
        print("STARTING NLP API")
        print("=" * 70)

        print(f"URL: {NLP_API_URL}")

        response = requests.post(
            NLP_API_URL,
            json=payload,
            timeout=120
        )

        print(
            f"NLP STATUS CODE: {response.status_code}"
        )

        response.raise_for_status()

        result_data = response.json()

        print("===== FINISHED NLP API =====")

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "message": "انتهت مهلة الاتصال بخادم NLP."
        }

    except requests.exceptions.ConnectionError:

        return {
            "success": False,
            "message": "تعذر الاتصال بخادم NLP."
        }

    except requests.exceptions.HTTPError:

        return {
            "success": False,
            "message": "حدث خطأ من خادم NLP.",
            "details": response.text
        }

    except requests.exceptions.RequestException as e:

        return {
            "success": False,
            "message": (
                f"حدث خطأ أثناء الاتصال بـ NLP: {str(e)}"
            )
        }

    except ValueError:

        return {
            "success": False,
            "message": (
                "خادم NLP أعاد استجابة ليست JSON صحيحة."
            )
        }

    # ============================================================
    # 3. استخراج graph
    # ============================================================

    graph_data = result_data.get("graph")

    if not graph_data:

        return {
            "success": False,
            "message": "لم يُرجع NLP أي graph."
        }

    if (
            "nodes" not in graph_data
            or "edges" not in graph_data
    ):

        return {
            "success": False,
            "message": (
                "الـgraph القادم من NLP "
                "لا يحتوي على nodes أو edges."
            )
        }

    print(
        f"NLP GRAPH: "
        f"{len(graph_data.get('nodes', []))} nodes, "
        f"{len(graph_data.get('edges', []))} edges"
    )

    # ============================================================
    # 4. تحديد المسارات
    # ============================================================

    PROJECT_ROOT = os.path.abspath(
        str(settings.BASE_DIR)
    )

    GRAPH_ENGINE_ROOT = os.path.join(
        PROJECT_ROOT,
        "graph_engine"
    )

    if not os.path.isdir(GRAPH_ENGINE_ROOT):

        return {
            "success": False,
            "message": (
                "لم يتم العثور على مجلد graph_engine:\n"
                f"{GRAPH_ENGINE_ROOT}"
            )
        }

    print(
        f"GRAPH ENGINE ROOT:\n{GRAPH_ENGINE_ROOT}"
    )

    # ============================================================
    # 5. حفظ NLP graph
    # ============================================================

    nlp_directory = os.path.join(
        GRAPH_ENGINE_ROOT,
        "nlp"
    )

    os.makedirs(
        nlp_directory,
        exist_ok=True
    )

    nlp_output_file = os.path.join(
        nlp_directory,
        "nlp4_output.json"
    )

    graph_to_save = dict(graph_data)

    if (
            "subject" not in graph_to_save
            and lesson.subject
    ):
        graph_to_save["subject"] = (
            lesson.subject.name
        )

    try:

        with open(
                nlp_output_file,
                "w",
                encoding="utf-8"
        ) as f:

            json.dump(
                graph_to_save,
                f,
                ensure_ascii=False,
                indent=4
            )

        print(
            "\nNLP graph saved to:"
        )
        print(nlp_output_file)

    except OSError as e:

        return {
            "success": False,
            "message": (
                "تعذر حفظ graph الناتج من NLP: "
                f"{str(e)}"
            )
        }

    # ============================================================
    # 6. مجلد SNA
    # ============================================================

    sna_directory = os.path.join(
        GRAPH_ENGINE_ROOT,
        "sna"
    )

    results_directory = os.path.join(
        sna_directory,
        "results"
    )

    os.makedirs(
        results_directory,
        exist_ok=True
    )

    # ============================================================
    # 7. التحقق من ملفات الـpipeline
    # ============================================================

    pipeline_files = [
        os.path.join(
            GRAPH_ENGINE_ROOT,
            "createandupdategraph.py"
        ),

        os.path.join(
            GRAPH_ENGINE_ROOT,
            "filter_graph.py"
        ),

        os.path.join(
            sna_directory,
            "1_sna.py"
        ),

        os.path.join(
            sna_directory,
            "new_sna_impact2.py"
        ),

        os.path.join(
            sna_directory,
            "new_sna_edge_impact2.py"
        ),

        os.path.join(
            sna_directory,
            "new_sna_plot_graph.py"
        ),

        os.path.join(
            sna_directory,
            "new_sna_plot_graph_filtered.py"
        ),

        os.path.join(
            sna_directory,
            "antonym.py"
        ),
    ]

    missing_pipeline_files = [
        path
        for path in pipeline_files
        if not os.path.isfile(path)
    ]

    if missing_pipeline_files:

        return {
            "success": False,
            "message": (
                    "ملفات الـpipeline التالية غير موجودة:\n"
                    + "\n".join(missing_pipeline_files)
            )
        }

    # ============================================================
    # 8. تعريف خطوات الـpipeline
    #
    # نستخدم المسارات المطلقة بدل الاعتماد على cwd
    # ============================================================

    pipeline_steps = [

        {
            "name": "createandupdategraph.py",
            "cwd": GRAPH_ENGINE_ROOT,
            "script": os.path.join(
                GRAPH_ENGINE_ROOT,
                "createandupdategraph.py"
            ),
            "args": [
                os.path.join(
                    GRAPH_ENGINE_ROOT,
                    "nlp",
                    "nlp4_output.json"
                )
            ],
            "timeout": 120,
        },

        {
            "name": "filter_graph.py",
            "cwd": GRAPH_ENGINE_ROOT,
            "script": os.path.join(
                GRAPH_ENGINE_ROOT,
                "filter_graph.py"
            ),
            "args": [],
            "timeout": 120,
        },

        {
            "name": "1_sna.py",
            "cwd": sna_directory,
            "script": os.path.join(
                sna_directory,
                "1_sna.py"
            ),
            "args": [],
            "timeout": 120,
        },

        {
            "name": "new_sna_impact2.py",
            "cwd": sna_directory,
            "script": os.path.join(
                sna_directory,
                "new_sna_impact2.py"
            ),
            "args": [],
            "timeout": 180,
        },

        {
            "name": "new_sna_edge_impact2.py",
            "cwd": sna_directory,
            "script": os.path.join(
                sna_directory,
                "new_sna_edge_impact2.py"
            ),
            "args": [],
            "timeout": 180,
        },

        {
            "name": "new_sna_plot_graph.py",
            "cwd": sna_directory,
            "script": os.path.join(
                sna_directory,
                "new_sna_plot_graph.py"
            ),
            "args": [],
            "timeout": 120,
        },

        {
            "name": "new_sna_plot_graph_filtered.py",
            "cwd": sna_directory,
            "script": os.path.join(
                sna_directory,
                "new_sna_plot_graph_filtered.py"
            ),
            "args": [],
            "timeout": 120,
        },

        {
            "name": "antonym.py",
            "cwd": sna_directory,
            "script": os.path.join(
                sna_directory,
                "antonym.py"
            ),
            "args": [],
            "timeout": 120,
        },
    ]

    # ============================================================
    # 9. تشغيل الـpipeline
    # ============================================================

    pipeline_outputs = []
    current_step = None

    pipeline_env = os.environ.copy()

    pipeline_env["PYTHONIOENCODING"] = "utf-8"
    pipeline_env["PYTHONUNBUFFERED"] = "1"

    # مهم جدًا على Windows
    pipeline_env["PYTHONUTF8"] = "1"

    try:

        for step in pipeline_steps:

            current_step = step["name"]

            script = step["script"]
            cwd = step["cwd"]
            args = step["args"]
            timeout = step["timeout"]

            command = [
                sys.executable,
                "-u",
                script,
                *args
            ]

            print("\n" + "=" * 70)
            print(
                f"STARTING: {step['name']}"
            )
            print("=" * 70)

            print(
                f"CWD: {cwd}"
            )

            print(
                f"PYTHON: {sys.executable}"
            )

            print(
                f"SCRIPT: {script}"
            )

            print(
                f"COMMAND: {command}"
            )

            print(
                f"TIMEOUT: {timeout} seconds"
            )

            # ----------------------------------------------------
            # تشغيل العملية
            # ----------------------------------------------------

            try:

                result = subprocess.run(
                    command,
                    cwd=cwd,
                    env=pipeline_env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout
                )

            except subprocess.TimeoutExpired as timeout_error:

                stdout_text = ""

                stderr_text = ""

                if timeout_error.stdout:

                    if isinstance(
                            timeout_error.stdout,
                            bytes
                    ):
                        stdout_text = (
                            timeout_error.stdout
                            .decode(
                                "utf-8",
                                errors="replace"
                            )
                        )
                    else:
                        stdout_text = str(
                            timeout_error.stdout
                        )

                if timeout_error.stderr:

                    if isinstance(
                            timeout_error.stderr,
                            bytes
                    ):
                        stderr_text = (
                            timeout_error.stderr
                            .decode(
                                "utf-8",
                                errors="replace"
                            )
                        )
                    else:
                        stderr_text = str(
                            timeout_error.stderr
                        )

                print(
                    "\nTIMEOUT!"
                )

                print(
                    f"STEP: {step['name']}"
                )

                print(
                    f"TIMEOUT: {timeout} seconds"
                )

                print(
                    "STDOUT BEFORE TIMEOUT:"
                )

                print(stdout_text)

                print(
                    "STDERR BEFORE TIMEOUT:"
                )

                print(stderr_text)

                pipeline_outputs.append(
                    {
                        "script": step["name"],
                        "return_code": None,
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                        "timeout": True,
                    }
                )

                return {
                    "success": False,
                    "message": (
                        "انتهت مهلة تشغيل "
                        f"{step['name']} بعد "
                        f"{timeout} ثانية."
                    ),
                    "current_step": step["name"],
                    "pipeline_outputs": pipeline_outputs
                }

            # ----------------------------------------------------
            # انتهاء العملية
            # ----------------------------------------------------

            print("\n" + "=" * 70)
            print(
                f"FINISHED: {step['name']}"
            )
            print("=" * 70)

            print(
                f"RETURN CODE: {result.returncode}"
            )

            print(
                "\nSTDOUT:"
            )

            print(result.stdout)

            print(
                "\nSTDERR:"
            )

            print(result.stderr)

            pipeline_outputs.append(
                {
                    "script": step["name"],
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )

            # ----------------------------------------------------
            # فشل العملية
            # ----------------------------------------------------

            if result.returncode != 0:

                return {
                    "success": False,
                    "message": (
                        f"فشل تشغيل {step['name']}."
                    ),
                    "current_step": step["name"],
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "pipeline_outputs": pipeline_outputs
                }

    except Exception as e:

        print(
            "\nPIPELINE EXCEPTION:"
        )

        print(str(e))

        return {
            "success": False,
            "message": (
                "حدث خطأ أثناء تشغيل الـpipeline: "
                f"{str(e)}"
            ),
            "current_step": current_step,
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 10. التأكد من story_elements.json
    # ============================================================

    story_elements_file = os.path.join(
        results_directory,
        "story_elements.json"
    )

    print(
        "\nChecking story_elements:"
    )

    print(
        story_elements_file
    )

    if not os.path.isfile(
            story_elements_file
    ):

        return {
            "success": False,
            "message": (
                "انتهى الـpipeline لكن لم يتم العثور "
                "على story_elements.json:\n"
                f"{story_elements_file}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 11. قراءة story_elements
    # ============================================================

    try:

        with open(
                story_elements_file,
                "r",
                encoding="utf-8"
        ) as f:

            story_elements = json.load(f)

    except (
            OSError,
            json.JSONDecodeError
    ) as e:

        return {
            "success": False,
            "message": (
                "تعذر قراءة story_elements.json: "
                f"{str(e)}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    print(
        "\n===== story_elements.json FOUND ====="
    )

    # ============================================================
    # 12. creatingStory
    # ============================================================

    creating_story_directory = os.path.join(
        GRAPH_ENGINE_ROOT,
        "creatingStory"
    )

    creating_story_file = os.path.join(
        creating_story_directory,
        "creatingStory.py"
    )

    if not os.path.isfile(
            creating_story_file
    ):

        return {
            "success": False,
            "message": (
                "لم يتم العثور على creatingStory.py:\n"
                f"{creating_story_file}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 13. ملفات creatingStory
    # ============================================================

    sna_graph_path = os.path.join(
        results_directory,
        "sna_plot_graph.json"
    )

    sna_graph_filtered_path = os.path.join(
        results_directory,
        "sna_plot_graph_filtered.json"
    )

    antonym_plot_path = os.path.join(
        results_directory,
        "antonym_plot.json"
    )

    # ============================================================
    # 14. الملفات الأساسية
    # ============================================================

    required_story_files = [
        sna_graph_path,
        sna_graph_filtered_path,
        story_elements_file
    ]

    missing_story_files = [
        path
        for path in required_story_files
        if not os.path.isfile(path)
    ]

    if missing_story_files:

        return {
            "success": False,
            "message": (
                    "creatingStory يحتاج ملفات أساسية "
                    "لم يتم توليدها:\n"
                    + "\n".join(missing_story_files)
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 15. antonym_plot.json اختياري
    # ============================================================

    if os.path.isfile(
            antonym_plot_path
    ):

        antonym_input_path = (
            antonym_plot_path
        )

        antonym_available = True

        print(
            "\n===== antonym_plot.json FOUND ====="
        )

    else:

        antonym_input_path = None

        antonym_available = False

        print(
            "\n===== antonym_plot.json NOT FOUND ====="
        )

        print(
            "This is allowed for this story type."
        )

    # ============================================================
    # 16. Gemini API Key
    # ============================================================

    gemini_api_key = os.environ.get(
        "GEMINI_API_KEY"
    )

    if not gemini_api_key:

        return {
            "success": False,
            "message": (
                "لم يتم العثور على GEMINI_API_KEY "
                "في Environment Variables."
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 17. تحميل creatingStory.py
    # ============================================================

    try:

        module_name = (
            "creatingStory_module"
        )

        spec = (
            importlib.util
            .spec_from_file_location(
                module_name,
                creating_story_file
            )
        )

        if (
                spec is None
                or spec.loader is None
        ):

            return {
                "success": False,
                "message": (
                    "تعذر تحميل creatingStory.py."
                ),
                "pipeline_outputs": pipeline_outputs
            }

        creating_story_module = (
            importlib.util
            .module_from_spec(spec)
        )

        spec.loader.exec_module(
            creating_story_module
        )

    except Exception as e:

        return {
            "success": False,
            "message": (
                "حدث خطأ أثناء تحميل "
                "creatingStory.py: "
                f"{str(e)}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 18. التأكد من الدالة
    # ============================================================

    if not hasattr(
            creating_story_module,
            "create_and_enhance_story"
    ):

        return {
            "success": False,
            "message": (
                "creatingStory.py لا يحتوي على "
                "الدالة create_and_enhance_story."
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 19. تشغيل creatingStory
    # ============================================================

    try:

        print("\n" + "=" * 70)
        print("STARTING creatingStory")
        print("=" * 70)

        print(
            f"sna_graph_path:\n{sna_graph_path}"
        )

        print(
            f"antonym_plot_path:\n{antonym_input_path}"
        )

        print(
            "sna_graph_filtered_path:\n"
            f"{sna_graph_filtered_path}"
        )

        print(
            "story_elements_path:\n"
            f"{story_elements_file}"
        )

        story_result = (
            creating_story_module
            .create_and_enhance_story(
                sna_graph_path=sna_graph_path,
                antonym_plot_path=antonym_input_path,
                sna_graph_filtered_path=sna_graph_filtered_path,
                story_elements_path=story_elements_file,
                api_key=gemini_api_key,
                seed=None
            )
        )

        print(
            "\n" + "=" * 70
        )

        print(
            "FINISHED creatingStory"
        )

        print(
            "=" * 70
        )

    except Exception as e:

        return {
            "success": False,
            "message": (
                "فشل تشغيل creatingStory: "
                f"{str(e)}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 20. التحقق من نتيجة creatingStory
    # ============================================================

    if not isinstance(
            story_result,
            dict
    ):

        return {
            "success": False,
            "message": (
                "creatingStory لم يُرجع "
                "نتيجة بصيغة dictionary."
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 21. استخراج القصة
    # ============================================================

    original_story = (
        story_result.get(
            "original_story"
        )
    )

    enhanced_story = (
        story_result.get(
            "enhanced_story"
        )
    )

    if not original_story:

        return {
            "success": False,
            "message": (
                "creatingStory لم يُرجع "
                "القصة الأصلية."
            ),
            "pipeline_outputs": pipeline_outputs
        }

    if not enhanced_story:

        return {
            "success": False,
            "message": (
                "Gemini لم يُرجع "
                "القصة المحسنة."
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 22. حفظ ملفات القصة
    # ============================================================

    generated_story_file = os.path.join(
        creating_story_directory,
        "generated_story.txt"
    )

    final_story_file = os.path.join(
        creating_story_directory,
        "final_story.txt"
    )

    try:

        with open(
                generated_story_file,
                "w",
                encoding="utf-8"
        ) as f:

            f.write(
                str(original_story)
            )

        with open(
                final_story_file,
                "w",
                encoding="utf-8"
        ) as f:

            f.write(
                str(enhanced_story)
            )

    except OSError as e:

        return {
            "success": False,
            "message": (
                "تم توليد القصة لكن فشل حفظ "
                "ملفات creatingStory: "
                f"{str(e)}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 23. حفظ StoryHistory
    # ============================================================

    try:

        with transaction.atomic():

            history = (
                StoryHistory.objects.create(
                    user=user,
                    lesson=lesson,
                    enhanced_story=str(
                        enhanced_story
                    )
                )
            )

    except Exception as e:

        return {
            "success": False,
            "message": (
                "تم تنفيذ الـpipeline وتوليد "
                "القصة، لكن فشل حفظ النتيجة "
                "في History: "
                f"{str(e)}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 24. النتيجة النهائية
    # ============================================================

    return {

        "success": True,

        "message": (
            "تم توليد القصة وتحسينها "
            "وحفظها في السجل بنجاح."
        ),

        "history_id": history.id,

        "lesson_id": lesson.id,

        "subject": lesson.subject.name,

        "story": str(
            enhanced_story
        ),

        "original_story": str(
            original_story
        ),

        "story_elements": story_elements,

        "antonym_plot_available": (
            antonym_available
        ),

        "files": {

            "nlp_output": (
                nlp_output_file
            ),

            "story_elements": (
                story_elements_file
            ),

            "sna_graph": (
                sna_graph_path
            ),

            "sna_graph_filtered": (
                sna_graph_filtered_path
            ),

            "antonym_plot": (
                antonym_input_path
            ),

            "generated_story": (
                generated_story_file
            ),

            "final_story": (
                final_story_file
            )
        },

        "pipeline_outputs": (
            pipeline_outputs
        )
    }