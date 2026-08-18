import json
import os
import subprocess
import sys
import importlib.util

from django.conf import settings
from django.db import transaction

from .models import Lesson, StoryHistory,Story


def generate_story_for_lesson(user, lesson_id):
    """
    توليد قصة للدرس عبر الـ NLP + Knowledge Graph + SNA + creatingStory.

    Pipeline الجديد:

    1. جلب الدرس.
    2. كتابة محتوى الدرس إلى:
           graph_engine/nlp/input_text.txt
    3. تشغيل run_pipeline.py.
       وهذا الملف يتولى:
           extract_lesson.py
           createandupdategraph.py
           filter_graph.py
           1_sna.py
           new_sna_impact2.py
           new_sna_edge_impact2.py
           new_sna_plot_graph.py
           new_sna_plot_graph_filtered.py
           antonym.py
    4. قراءة llm_output.json الناتج من extract_lesson.py.
    5. التأكد من ملفات SNA الناتجة.
    6. قراءة story_elements.json.
    7. تشغيل creatingStory.py.
    8. تحسين القصة بواسطة Gemini.
    9. حفظ القصة في StoryHistory.

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
    # 2. تحديد المسارات
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
        "\n" + "=" * 70
    )

    print(
        "GRAPH ENGINE ROOT:"
    )

    print(
        GRAPH_ENGINE_ROOT
    )

    print(
        "=" * 70
    )

    # ============================================================
    # 3. تحديد مجلد NLP
    # ============================================================

    nlp_directory = os.path.join(
        GRAPH_ENGINE_ROOT,
        "nlp"
    )

    if not os.path.isdir(nlp_directory):

        return {
            "success": False,
            "message": (
                "لم يتم العثور على مجلد nlp:\n"
                f"{nlp_directory}"
            )
        }

    # ============================================================
    # 4. كتابة محتوى الدرس إلى input_text.txt
    #
    # extract_lesson.py يعتمد على هذا الملف.
    # ============================================================

    input_text_file = os.path.join(
        nlp_directory,
        "input_text.txt"
    )

    try:

        with open(
                input_text_file,
                "w",
                encoding="utf-8"
        ) as f:

            f.write(
                lesson.content.strip()
            )

        print(
            "\n===== LESSON TEXT SAVED ====="
        )

        print(
            f"INPUT TEXT:\n{input_text_file}"
        )

    except OSError as e:

        return {
            "success": False,
            "message": (
                "تعذر كتابة محتوى الدرس إلى "
                "input_text.txt: "
                f"{str(e)}"
            )
        }

    # ============================================================
    # 5. ملفات الـpipeline
    #
    # Django الآن لا يشغل كل ملف بشكل منفصل.
    #
    # يشغل run_pipeline.py فقط.
    #
    # run_pipeline.py مسؤول عن تشغيل:
    #
    # extract_lesson.py
    # createandupdategraph.py
    # filter_graph.py
    # 1_sna.py
    # new_sna_impact2.py
    # new_sna_edge_impact2.py
    # new_sna_plot_graph.py
    # new_sna_plot_graph_filtered.py
    # antonym.py
    # ============================================================

    run_pipeline_file = os.path.join(
        GRAPH_ENGINE_ROOT,
        "run_pipeline.py"
    )

    if not os.path.isfile(
            run_pipeline_file
    ):

        return {
            "success": False,
            "message": (
                "لم يتم العثور على run_pipeline.py:\n"
                f"{run_pipeline_file}"
            )
        }

    # ============================================================
    # 6. مجلد SNA
    # ============================================================

    sna_directory = os.path.join(
        GRAPH_ENGINE_ROOT,
        "sna"
    )

    if not os.path.isdir(
            sna_directory
    ):

        return {
            "success": False,
            "message": (
                "لم يتم العثور على مجلد sna:\n"
                f"{sna_directory}"
            )
        }

    results_directory = os.path.join(
        sna_directory,
        "results"
    )

    os.makedirs(
        results_directory,
        exist_ok=True
    )

    # ============================================================
    # 7. ملفات الناتج المتوقعة من extract_lesson
    # ============================================================

    relation_extraction_file = os.path.join(
        nlp_directory,
        "relation_extraction.json"
    )

    # ============================================================
    # 8. تشغيل run_pipeline.py
    # ============================================================

    pipeline_outputs = []

    current_step = None

    pipeline_env = os.environ.copy()

    pipeline_env["PYTHONIOENCODING"] = "utf-8"
    pipeline_env["PYTHONUNBUFFERED"] = "1"

    # مهم جدًا على Windows
    pipeline_env["PYTHONUTF8"] = "1"

    pipeline_step = {
        "name": "run_pipeline.py",
        "cwd": GRAPH_ENGINE_ROOT,
        "script": run_pipeline_file,
        "args": [],
        "timeout": 900,
    }

    try:

        current_step = pipeline_step["name"]

        script = pipeline_step["script"]
        cwd = pipeline_step["cwd"]
        args = pipeline_step["args"]
        timeout = pipeline_step["timeout"]

        command = [
            sys.executable,
            "-u",
            script,
            *args
        ]

        print(
            "\n" + "=" * 70
        )

        print(
            "STARTING: run_pipeline.py"
        )

        print(
            "=" * 70
        )

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

        print(
            "\n" + "=" * 70
        )

        # --------------------------------------------------------
        # تشغيل العملية
        # --------------------------------------------------------

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
                "STEP: run_pipeline.py"
            )

            print(
                f"TIMEOUT: {timeout} seconds"
            )

            print(
                "\nSTDOUT BEFORE TIMEOUT:"
            )

            print(
                stdout_text
            )

            print(
                "\nSTDERR BEFORE TIMEOUT:"
            )

            print(
                stderr_text
            )

            pipeline_outputs.append(
                {
                    "script": "run_pipeline.py",
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
                    f"run_pipeline.py بعد "
                    f"{timeout} ثانية."
                ),
                "current_step": "run_pipeline.py",
                "pipeline_outputs": pipeline_outputs
            }

        # --------------------------------------------------------
        # انتهاء العملية
        # --------------------------------------------------------

        print(
            "\n" + "=" * 70
        )

        print(
            "FINISHED: run_pipeline.py"
        )

        print(
            "=" * 70
        )

        print(
            f"RETURN CODE: {result.returncode}"
        )

        print(
            "\nSTDOUT:"
        )

        print(
            result.stdout
        )

        print(
            "\nSTDERR:"
        )

        print(
            result.stderr
        )

        pipeline_outputs.append(
            {
                "script": "run_pipeline.py",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )

        # --------------------------------------------------------
        # فشل الـpipeline
        # --------------------------------------------------------

        if result.returncode != 0:

            return {
                "success": False,
                "message": (
                    "فشل تشغيل run_pipeline.py."
                ),
                "current_step": "run_pipeline.py",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "pipeline_outputs": pipeline_outputs
            }

    except Exception as e:

        print(
            "\nPIPELINE EXCEPTION:"
        )

        print(
            str(e)
        )

        return {
            "success": False,
            "message": (
                "حدث خطأ أثناء تشغيل "
                f"run_pipeline.py: {str(e)}"
            ),
            "current_step": current_step,
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 9. التأكد من llm_output.json
    #
    # هذا هو الناتج الجديد من extract_lesson.py.
    # ============================================================

    print(
        "\nChecking relation_extraction.json:"
    )

    print(
        relation_extraction_file
    )

    if not os.path.isfile(
            relation_extraction_file
    ):

        return {
            "success": False,
            "message": (
                "انتهى run_pipeline.py بنجاح "
                "لكن لم يتم العثور على relation_extraction.json:\n"
                f"{relation_extraction_file}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 10. قراءة llm_output.json
    # ============================================================

    try:

        with open(
                relation_extraction_file,
                "r",
                encoding="utf-8"
        ) as f:

            graph_data = json.load(f)

    except (
            OSError,
            json.JSONDecodeError
    ) as e:

        return {
            "success": False,
            "message": (
                "تعذر قراءة relation_extraction.json: "
                f"{str(e)}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 11. التحقق من graph
    # ============================================================

    if not graph_data:

        return {
            "success": False,
            "message": (
                "relation_extraction.json فارغ."
            ),
            "pipeline_outputs": pipeline_outputs
        }

    if (
            "nodes" not in graph_data
            or "edges" not in graph_data
    ):

        return {
            "success": False,
            "message": (
                "relation_extraction.json لا يحتوي على nodes أو edges."
            ),
            "pipeline_outputs": pipeline_outputs
        }

    print(
        "\n===== LLM OUTPUT FOUND ====="
    )

    print(
        f"LLM GRAPH: "
        f"{len(graph_data.get('nodes', []))} nodes, "
        f"{len(graph_data.get('edges', []))} edges"
    )

    # ============================================================
    # 12. إضافة subject إذا لم يكن موجودًا
    # ============================================================

    if (
            "subject" not in graph_data
            and lesson.subject
    ):

        graph_data["subject"] = (
            lesson.subject.name
        )

        # تحديث الملف بعد إضافة subject
        try:

            with open(
                    relation_extraction_file,
                    "w",
                    encoding="utf-8"
            ) as f:

                json.dump(
                    graph_data,
                    f,
                    ensure_ascii=False,
                    indent=4
                )

        except OSError as e:

            return {
                "success": False,
                "message": (
                    "تمت قراءة llm_output.json "
                    "لكن تعذر تحديث subject: "
                    f"{str(e)}"
                ),
                "pipeline_outputs": pipeline_outputs
            }

    # ============================================================
    # 13. التأكد من ملفات SNA الناتجة
    # ============================================================

    required_sna_files = [

        os.path.join(
            results_directory,
            "story_elements.json"
        ),

        os.path.join(
            results_directory,
            "sna_plot_graph.json"
        ),

        os.path.join(
            results_directory,
            "sna_plot_graph_filtered.json"
        ),
    ]

    missing_sna_files = [
        path
        for path in required_sna_files
        if not os.path.isfile(path)
    ]

    if missing_sna_files:

        return {
            "success": False,
            "message": (
                    "انتهى الـpipeline لكن بعض ملفات النتائج "
                    "المطلوبة لم يتم توليدها:\n"
                    + "\n".join(missing_sna_files)
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 14. story_elements.json
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
    # 15. قراءة story_elements
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
    # 16. creatingStory
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
    # 17. ملفات creatingStory
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
    # 18. الملفات الأساسية
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
    # 19. antonym_plot.json اختياري
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
    # 20. Gemini API Key
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
    # 21. تحميل creatingStory.py
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
    # 22. التأكد من الدالة
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
    # 23. تشغيل creatingStory
    # ============================================================

    try:

        print(
            "\n" + "=" * 70
        )

        print(
            "STARTING creatingStory"
        )

        print(
            "=" * 70
        )

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
    # 24. التحقق من نتيجة creatingStory
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
    # 25. استخراج القصة
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
    # 26. حفظ ملفات القصة
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
# 27. حفظ القصة في Story
# ============================================================

    try:

        with transaction.atomic():

            story = Story.objects.create(
                lesson=lesson,
                title="قصة تعليمية",
                content=str(enhanced_story),
                initial_rating=1,
                review_comment=None,
                is_favorite=False
            )

    except Exception as e:

        return {
            "success": False,
            "message": (
                "تم تنفيذ الـpipeline وتوليد "
                "القصة، لكن فشل حفظ القصة في Story: "
                f"{str(e)}"
            ),
            "pipeline_outputs": pipeline_outputs
        }

    # ============================================================
    # 28. النتيجة النهائية
    # ============================================================

    return {

        "success": True,

        "message": (
            "تم توليد القصة وتحسينها "
            "وحفظها في السجل بنجاح."
        ),

        "story_id": story.id,

        "lesson_id": lesson.id,

        "subject": (
            lesson.subject.name
            if lesson.subject
            else graph_data.get("subject")
        ),

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

            "input_text": (
                input_text_file
            ),

            "relation_extraction": (
                relation_extraction_file
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