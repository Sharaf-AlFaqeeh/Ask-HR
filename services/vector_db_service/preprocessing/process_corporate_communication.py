import os
import re
from pathlib import Path
import pdfplumber

# 1. تحديد المسارات الأساسية
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

# اسم المجلد الهدف
TARGET_FOLDER_NAME = "سياسات الاتصال المؤسسي"

SOURCE_FOLDER = BASE_DIR / "HSA_policies" / TARGET_FOLDER_NAME
OUTPUT_FOLDER = BASE_DIR / "extracted_texts" / TARGET_FOLDER_NAME

def clean_arabic_text(text):
    """
    فلتر مخصص للنصوص العربية فقط.
    يقوم بعكس السطر ليعود مقروءاً، مع الحفاظ على اتجاه الأرقام والأقواس.
    """
    if not text:
        return ""
    
    lines = str(text).split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 1. عكس السطر بالكامل لتصحيح اتجاه الحروف العربية
        reversed_line = line[::-1]
        
        # 2. تنظيف التطويل (الكشيدة)
        reversed_line = reversed_line.replace('ـ', '')
        
        # 3. تصحيح الأقواس التي انقلبت
        reversed_line = reversed_line.replace(')', '\x00').replace('(', ')').replace('\x00', '(')
        reversed_line = reversed_line.replace(']', '\x00').replace('[', ']').replace('\x00', '[')
        
        # 4. الحفاظ على اتجاه الأرقام أو الكلمات الإنجليزية العابرة (إن وُجدت صدفة)
        def fix_numbers_and_english(match):
            return match.group(0)[::-1]
        
        final_line = re.sub(r'[A-Za-z0-9]+', fix_numbers_and_english, reversed_line)
        
        processed_lines.append(final_line)
        
    return '\n'.join(processed_lines)

def extract_text_only(pdf_path):
    """استخراج النصوص فقط (بدون البحث عن جداول) لزيادة السرعة"""
    full_content = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                full_content += f"--- بداية الصفحة ({page_num + 1}) ---\n\n"
                
                text = page.extract_text()
                if text:
                    full_content += clean_arabic_text(text) + "\n\n"
                    
    except Exception as e:
        print(f"حدث خطأ أثناء معالجة {pdf_path.name}: {e}")
        
    return full_content

def process_corp_comm_directory():
    # إنشاء مجلد المخرجات
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FOLDER.exists():
        print(f"تنبيه: المسار المصدر غير موجود: {SOURCE_FOLDER}")
        return

    print(f"بدء استخراج النصوص العربية الصافية لملفات: ({TARGET_FOLDER_NAME})...\n" + "="*50)

    pdf_files = list(SOURCE_FOLDER.glob("*.pdf"))
    if not pdf_files:
        print("لا توجد ملفات PDF في هذا المجلد.")
        return

    for pdf_path in pdf_files:
        print(f"جاري استخراج: {pdf_path.name}")
        
        ar_content = extract_text_only(pdf_path)
        
        if ar_content.strip():
            # حفظ الملف بصيغة txt مباشرة
            text_filename = pdf_path.stem + ".txt"
            output_file_path = OUTPUT_FOLDER / text_filename
            
            with open(output_file_path, "w", encoding="utf-8") as text_file:
                text_file.write(ar_content)
                
            print(f"    ✓ تم الحفظ بنجاح: {text_filename}")
        else:
            print(f"    ⚠ تحذير: الملف فارغ: {pdf_path.name}")

if __name__ == "__main__":
    process_corp_comm_directory()
    print("="*50 + "\nاكتملت العملية للمجلد الثالث بسلاسة!")