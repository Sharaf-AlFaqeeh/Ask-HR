import os
import json
import requests
import time
from pathlib import Path

# إعدادات المسارات والمجلدات
BASE_DIR = r"P:\____AI____\HSAGroup\AskHRPro\services\vector_db_service"
INPUT_DIR = os.path.join(BASE_DIR, "extracted_texts")

OUTPUT_DIR = os.path.join(BASE_DIR, "structured_texts_md")

# مصفوفة بأسماء المجلدات المراد تحليله
TARGET_FOLDERS = [
    # "تكنولوجيا المعلومات",
    # "سياسات الاتصال المؤسسي",
    # "سياسات الامتثال و الحوكمة",
    "سياسات التواصل الداخلي",
    # "سياسات الصحة والسلامة المهنية",
    # "سياسات المالية",
    # "سياسات المشتريات",
    # "سياسات الموارد البشريه"

]

# إعدادات خادم LLM المحلي
LLM_API_URL = "http://localhost:8000/v1/chat/completions"
# الخادم يستخدم "qwen2.5" كافتراضي
MODEL_NAME = "qwen2.5" 
MAX_TOKENS = 2000
TEMPERATURE = 0.1 # درجة حرارة منخفضة جداً لضمان الدقة وعدم الهلوسة

# هندسة الأوامر (Prompt Engineering)
# SYSTEM_PROMPT = """أنت خبير في هيكلة البيانات (Data Structuring) ومعالجة المستندات باللغة العربية.
# مهمتك هي أخذ نص تم استخراجه بواسطة تقنيات OCR من ملفات سياسات الموارد البشرية، والذي يعاني من تداخل في الأسطر وتشوه في التنسيق، وإعادة بناء هيكله بالكامل.

# عليك الالتزام بالقواعد التالية بصرامة:
# 1. التنسيق المطلوب: أعد كتابة النص باستخدام تنسيق Markdown.
# 2. العناوين: استخدم (##) للعناوين الرئيسية (مثل: الفلسفة، نطاق التطبيق، التعريفات، بنود السياسة).
# 3. المواد القانونية: اجعل كل مادة تبدأ بسطر جديد وميزها بخط عريض، مثال: **مادة (1):**
# 4. القوائم: قم بتنسيق النقاط (أ، ب، ت) أو (1، 2، 3) كقوائم نقطية أو رقمية منظمة.
# 5. التنظيف: احذف أي أرقام هواتف، أرقام تذييل (Footers)، أو شفرات غير مفهومة تظهر في نهاية النص.
# 6. التصحيح الإملائي: قم بإصلاح الأخطاء الإملائية الواضحة الناتجة عن الـ OCR (مثل: "الذيتم" إلى "الذي تم")، ولكن *لا تقم بتغيير المعنى أو إضافة معلومات من عندك نهائياً*.
# 7. المخرجات: أخرج النص بصيغة Markdown فقط، بدون أي مقدمات أو شروحات.
# """
SYSTEM_PROMPT = """أنت خبير في هيكلة البيانات (Data Structuring) ومعالجة المستندات باللغة العربية.
مهمتك هي أخذ نص تم استخراجه بواسطة تقنيات OCR من ملفات سياسات الموارد البشرية، والذي يعاني من تداخل في الأسطر وتشوه في التنسيق، وإعادة بناء هيكله بالكامل.

عليك الالتزام بالقواعد التالية بصرامة تامة:
1. التطابق الكامل (يمنع الاختصار): يمنع منعاً باتاً اختصار النص أو تلخيصه أو حذف أي فقرة أو مادة قانونية. يجب أن يحتوي مخرجك على كل كلمة موجودة في النص الأصلي بالتمام والكمال.
2. التنسيق المطلوب: أعد ترتيب النص باستخدام تنسيق Markdown.
3. العناوين: استخدم (##) للعناوين الرئيسية (مثل: الفلسفة، نطاق التطبيق، التعريفات، بنود السياسة).
4. المواد القانونية: اجعل كل مادة تبدأ بسطر جديد وميزها بخط عريض، مثال: **مادة (1):**
5. القوائم: قم بتنسيق النقاط (أ، ب، ت) أو (1، 2، 3) كقوائم نقطية أو رقمية منظمة.
6. التنظيف: احذف فقط أرقام الهواتف، أرقام الصفحات (Footers)، أو الشفرات العشوائية الملتصقة بنهاية النص.
7. التصحيح الإملائي: أصلح الأخطاء الناتجة عن الـ OCR فقط (مثل: "الذيتم" إلى "الذي تم").
8. المخرجات: أخرج النص بصيغة Markdown فقط، بدون أي مقدمات أو شروحات.
"""

def process_text_with_llm(text_content: str, filename: str) -> str:
    """إرسال النص إلى النموذج اللغوي المحلي لإعادة هيكلته"""
    
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"النص المستخرج من ملف ({filename}):\n\n{text_content}"}
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS
    }
    
    try:
        print(f"   🤖 جاري معالجة {filename} عبر LLM...")
        start_time = time.time()
        response = requests.post(LLM_API_URL, headers=headers, json=payload)
        response.raise_for_status() # للتحقق من نجاح الاتصال
        
        result = response.json()
        structured_text = result["choices"][0]["message"]["content"]
        
        duration = round(time.time() - start_time, 2)
        print(f"   ✅ تمت المعالجة بنجاح في {duration} ثانية.")
        
        return structured_text
        
    except Exception as e:
        print(f"   ❌ حدث خطأ أثناء الاتصال بالنموذج لملف {filename}: {str(e)}")
        return ""

#  دورة المعالجة الرئيسية
def main():
    print("🚀 بدء خط أنابيب إعادة الهيكلة باستخدام LLM...")
    
    # التأكد من وجود المجلد الرئيسي للمخرجات
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for folder_name in TARGET_FOLDERS:
        input_folder_path = os.path.join(INPUT_DIR, folder_name)
        output_folder_path = os.path.join(OUTPUT_DIR, folder_name)
        
        if not os.path.exists(input_folder_path):
            print(f"⚠️ المجلد '{folder_name}' غير موجود في المسار، سيتم تخطيه.")
            continue
            
        print(f"\n📂 جاري معالجة مجلد: {folder_name}")
        os.makedirs(output_folder_path, exist_ok=True)
        
        # جلب جميع ملفات النص من المجلد
        txt_files = list(Path(input_folder_path).glob("*.txt"))
        
        if not txt_files:
            print(f"   - لا توجد ملفات txt في هذا المجلد.")
            continue
            
        for txt_file in txt_files:
            print(f"\n📄 قراءة الملف: {txt_file.name}")
            
            with open(txt_file, 'r', encoding='utf-8') as f:
                raw_text = f.read()
                
            if not raw_text.strip():
                print("   - الملف فارغ، سيتم التخطي.")
                continue
                
            # إرسال النص للنموذج
            structured_markdown = process_text_with_llm(raw_text, txt_file.name)
            
            if structured_markdown:
                # حفظ النتيجة بلاحقة .md
                output_filename = txt_file.stem + "_structured.md"
                output_filepath = os.path.join(output_folder_path, output_filename)
                
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(structured_markdown)
                print(f"   💾 تم الحفظ: {output_filepath}")

if __name__ == "__main__":
    main()