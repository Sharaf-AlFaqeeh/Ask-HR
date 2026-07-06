import os
import re
import requests
import time
import tiktoken
from pathlib import Path

# 1. إعدادات المسارات والمجلدات
BASE_DIR = r"P:\____AI____\HSAGroup\AskHRPro\services\vector_db_service"
INPUT_DIR = os.path.join(BASE_DIR, "extracted_texts")
OUTPUT_DIR = os.path.join(BASE_DIR, "structured_texts_md")


TARGET_FOLDERS = [
    "تكنولوجيا المعلومات",
    "سياسات الاتصال المؤسسي",
    "سياسات الامتثال و الحوكمة",
    "سياسات التواصل الداخلي",
    # "سياسات الصحة والسلامة المهنية",
    # "سياسات المالية",
    # "سياسات المشتريات",
    # "سياسات الموارد البشريه"

]

# 2. إعدادات النموذج والتوكنز
LLM_API_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "qwen2.5" 
MAX_TOKENS = 2000
TEMPERATURE = 0.1 

try:
    tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception as e:
    print("❌ يرجى تثبيت مكتبة tiktoken")
    exit()

# 3. هندسة الأوامر (الاستراتيجية المتسلسلة)

# البرومبت الأول: التركيز فقط على الهيكلة وتحويل الصفحات
PROMPT_PHASE_1 = """أنت خبير في تحويل النصوص العادية إلى تنسيق Markdown.
مهمتك استلام نص مستخرج من PDF وإعادة هيكلته بناءً على القواعد التالية فقط:
1. حول علامات الصفحات (مثل: --- بداية الصفحة (1) ---) إلى ترويسة رئيسية (## الصفحة 1).
2. حافظ على الجداول إذا كانت سليمة، أو حاول دمجها إذا كانت مقطعة.
3. استخدم (**) للعناوين الرئيسية والمواد القانونية (مثل: **مادة 1:**).
4. استخدم التنسيق النقطي (-) للتعريفات والقوائم.
5. لا تقم باختصار النص، ولا تحذف أي فقرات، ولا تضف أي مقدمات من عندك.
أخرج النص بصيغة Markdown فقط."""

# البرومبت الثاني: التركيز فقط على التصحيح الإملائي البصري (OCR)
PROMPT_PHASE_2 = """أنت مدقق لغوي دقيق.
مهمتك استلام نص بصيغة Markdown وتصحيح أخطاء الاستخراج البصري (OCR) فيه مع الحفاظ على تنسيق Markdown كما هو تماماً.
القواعد:
1. ادمج الحروف المفصولة (مثال: "خليف ة" تصبح "خليفة"، "حن ا" تصبح "حنا").
2. صحح الكلمات الإنجليزية المعكوسة (مثال: "liam-E" تصبح "E-mail"، "ygolonhceT" تصبح "Technology").
3. صحح تشوهات الترميز الواضحة (مثل: "الأدوار" تصبح "الأدوار").
4. لا تغير أي عناوين أو أرقام صفحات (## الصفحة).
5. لا تغير صياغة الجمل، ولا تقم باختصار النص نهائياً.
أخرج النص المصحح بصيغة Markdown فقط."""

# 4. دوال المعالجة
def get_token_count(text: str) -> int:
    return len(tokenizer.encode(text))

def pre_clean_text(text: str) -> str:
    """تنظيف برمجي سريع لتخفيف العبء عن النموذج"""
    text = text.replace("[تم العثور على جدول في هذه الصفحة]:", "")
    text = re.sub(r'\[النصوص المصاحبة.*?\].*?(?=--- بداية الصفحة|\Z)', '', text, flags=re.DOTALL)
    return text.strip()

def chunk_text_by_tokens(text: str, max_chunk_tokens: int = 1500) -> list:
    lines = text.split('\n')
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for line in lines:
        if not line.strip(): continue
        line_tokens = get_token_count(line)
        
        if line_tokens > max_chunk_tokens:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
                current_tokens = 0
            chunks.append(line)
            continue
            
        if current_tokens + line_tokens > max_chunk_tokens:
            chunks.append(current_chunk)
            current_chunk = line
            current_tokens = line_tokens
        else:
            current_chunk += "\n" + line if current_chunk else line
            current_tokens += line_tokens
            
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def process_text_with_llm(text_content: str, system_prompt: str, log_label: str) -> str:
    """دالة مرنة ترسل النص للنموذج مع البرومبت المحدد"""
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{text_content}"}
        ],
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS
    }
    
    try:
        start_time = time.time()
        response = requests.post(LLM_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        result_text = response.json()["choices"][0]["message"]["content"]
        duration = round(time.time() - start_time, 2)
        print(f"      ✅ تمت {log_label} في {duration} ثانية.")
        return result_text.strip()
    except Exception as e:
        print(f"      ❌ خطأ أثناء {log_label}: {str(e)}")
        return text_content # إرجاع النص كما هو في حالة الفشل

# 5. دورة العمل الرئيسية (التنظيف -> التقطيع -> المعالجة المزدوجة)
def main():
    print("🚀 بدء خط أنابيب إعادة الهيكلة (الاستراتيجية المزدوجة)...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for folder_name in TARGET_FOLDERS:
        input_folder_path = os.path.join(INPUT_DIR, folder_name)
        output_folder_path = os.path.join(OUTPUT_DIR, folder_name)
        
        if not os.path.exists(input_folder_path): continue
            
        print(f"\n📂 جاري معالجة: {folder_name}")
        os.makedirs(output_folder_path, exist_ok=True)
        txt_files = list(Path(input_folder_path).glob("*.txt"))
        
        for txt_file in txt_files:
            print(f"\n📄 قراءة: {txt_file.name}")
            with open(txt_file, 'r', encoding='utf-8') as f:
                raw_text = f.read()
                
            if not raw_text.strip(): continue
            
            # التنظيف البرمجي السريع أولاً
            cleaned_text = pre_clean_text(raw_text)
            tokens = get_token_count(cleaned_text)
            print(f"   🔢 الحجم بعد التنظيف البرمجي: {tokens} توكن")
            
            final_markdown = ""
            
            # تحديد الأجزاء (إذا كان صغيراً سيكون جزءاً واحداً)
            if tokens <= MAX_TOKENS:
                chunks = [cleaned_text]
                print("   🟢 إرسال الملف كدفعة واحدة...")
            else:
                chunks = chunk_text_by_tokens(cleaned_text, max_chunk_tokens=1500)
                print(f"   🔴 تفعيل التقطيع: {len(chunks)} أجزاء.")
                
            # المعالجة المزدوجة لكل جزء
            for i, chunk in enumerate(chunks):
                chunk_label = f"الجزء {i+1}/{len(chunks)}"
                print(f"   ⏳ معالجة {chunk_label}:")
                
                # المرحلة 1: الهيكلة
                phase1_md = process_text_with_llm(chunk, PROMPT_PHASE_1, "المرحلة الأولى (الهيكلة)")
                
                # المرحلة 2: التصحيح البصري
                phase2_md = process_text_with_llm(phase1_md, PROMPT_PHASE_2, "المرحلة الثانية (التصحيح)")
                
                final_markdown += phase2_md + "\n\n"
            
            # الحفظ
            if final_markdown:
                output_filepath = os.path.join(output_folder_path, txt_file.stem + "_structured.md")
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(final_markdown)
                print(f"   💾 تم الحفظ: {txt_file.stem}_structured.md")

if __name__ == "__main__":
    main()