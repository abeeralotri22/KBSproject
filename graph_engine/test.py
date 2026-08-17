import requests
import json


API_URL = "https://judy4444-text2tale-nlp.hf.space/generate_graph"

payload = {
    "text": """قبل آلاف السنين، عاش القدماء المصريون على ضفاف نهر النيل.
وكان لديهم حكام يلقبون بالفراعنة.
اعتقد هؤلاء الملوك أن هناك حياة ثانية بعد الموت، لذلك قرروا بناء مقابر ضخمة وقوية لحماية أنفسهم وأموالهم.
أشهر هذه المقابر هي أهرامات الجيزة الثلاثة، وأكبرها الهرم الأكبر الذي بناه الملك خوفو.
لم تكن هناك رافعات أو آلات حديثة في ذلك الوقت.
لذلك، تعاون آلاف العمال المصريين بذكاء وصبر شديد.
قاموا بقطع الحجارة الضخمة من الجبال، ونقلوها عبر نهر النيل، ثم رفعوها فوق بعضها بدقة عالية باستخدام ممرات طينية مائلة."""
}

try:
    print("جاري إرسال النص إلى الخادم للتحليل...")
    
    response = requests.post(API_URL, json=payload, timeout=120)
    
    # التحقق من نجاح الطلب (كود 200)
    response.raise_for_status()
    
    # 4. تحويل الرد إلى قاموس بايثون (Dictionary)
    result_data = response.json()
    
    print("\n تم الاستلام بنجاح!")
    

    print("\n--- العلاقات المستخرجة ---")
    for triplet in result_data.get("triplets", []):
        print(f"[{triplet[0]}] --({triplet[1]})--> [{triplet[2]}]")
        

    print("\n--- الغراف المعرفي (JSON) ---")
    print(json.dumps(result_data.get("graph", {}), ensure_ascii=False, indent=2))

except requests.exceptions.HTTPError as http_err:
    print(f"❌ خطأ من الخادم: {http_err}")
    print(f"التفاصيل: {response.text}")
except requests.exceptions.ConnectionError:
    print("❌ خطأ: تعذر الاتصال بالخادم. تأكدي من أن الـ Space قيد التشغيل (Running).")
except Exception as e:
    print(f"❌ حدث خطأ غير متوقع: {e}")