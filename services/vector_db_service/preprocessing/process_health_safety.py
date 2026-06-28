import os
import re
from pathlib import Path
import pdfplumber

# 1. تحديد المسارات الأساسية
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

TARGET_FOLDER_NAME = "سياسات الصحة والسلامة المهنية"

SOURCE_FOLDER = BASE_DIR / "HSA_policies" / TARGET_FOLDER_NAME
OUTPUT_FOLDER = BASE_DIR / "extracted_texts" / TARGET_FOLDER_NAME

def clean_cell_text(text):
    """
    فلتر مخصص لخلايا الجداول.
    يعكس النص العربي، يحافظ على الأرقام، ويدمج الأسطر المتعددة في سطر واحد 
    لضمان عدم تشوه هيكل الجدول في ملف الـ txt.
    """
    if not text:
        return " "
    
    lines = str(text).split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 1. عكس السطر بالكامل
        reversed_line = line[::-1]
        
        # 2. تنظيف التطويل (الكشيدة)
        reversed_line = reversed_line.replace('ـ', '')
        
        # 3. تصحيح الأقواس
        reversed_line = reversed_line.replace(')', '\x00').replace('(', ')').replace('\x00', '(')
        reversed_line = reversed_line.replace(']', '\x00').replace('[', ']').replace('\x00', '[')
        
        # 4. إصلاح الأرقام والكلمات الإنجليزية والكسور العشرية (مثل 1.5)
        def fix_numbers_and_english(match):
            return match.group(0)[::-1]
        
        final_line = re.sub(r'[A-Za-z0-9\.]+', fix_numbers_and_english, reversed_line)
        
        processed_lines.append(final_line)
        
    # دمج الأسطر بمسافة بدلاً من سطر جديد للحفاظ على شكل الخلية في Markdown
    return ' '.join(processed_lines)

def format_table_to_markdown(table):
    """تحويل المصفوفة المستخرجة إلى جدول نصي مقروء وتطبيق الفلتر على كل خلية"""
    if not table:
        return ""
    
    markdown_lines = []
    for i, row in enumerate(table):
        # تطبيق الفلتر على كل خلية وتنظيف الفراغات
        cleaned_row = [clean_cell_text(cell).strip() if cell else " " for cell in row]
        
        # رص عناصر الصف يفصل بينها |
        line = "| " + " | ".join(cleaned_row) + " |"
        markdown_lines.append(line)
        
        # إضافة خط فاصل بعد الهيدر (الصف الأول)
        if i == 0:
            separator = "| " + " | ".join(["---"] * len(row)) + " |"
            markdown_lines.append(separator)
            
    return "\n".join(markdown_lines) + "\n\n"

def extract_tables_only(pdf_path):
    """التركيز حصرياً على سحب الجداول من جميع الصفحات"""
    full_content = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                if tables:
                    full_content += f"--- جداول الصفحة ({page_num + 1}) ---\n\n"
                    for idx, table in enumerate(tables):
                        full_content += f"[الجدول {idx + 1}]:\n"
                        full_content += format_table_to_markdown(table)
                        
    except Exception as e:
        print(f"حدث خطأ أثناء معالجة {pdf_path.name}: {e}")
        
    return full_content

def process_health_safety_directory():
    # إنشاء مجلد المخرجات
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FOLDER.exists():
        print(f"تنبيه: المسار المصدر غير موجود: {SOURCE_FOLDER}")
        return

    print(f"بدء كشط الجداول لملفات: ({TARGET_FOLDER_NAME})...\n" + "="*50)

    pdf_files = list(SOURCE_FOLDER.glob("*.pdf"))
    if not pdf_files:
        print("لا توجد ملفات PDF في هذا المجلد.")
        return

    for pdf_path in pdf_files:
        print(f"جاري كشط الجداول من: {pdf_path.name}")
        
        ar_content = extract_tables_only(pdf_path)
        
        if ar_content.strip():
            text_filename = pdf_path.stem + ".txt"
            output_file_path = OUTPUT_FOLDER / text_filename
            
            with open(output_file_path, "w", encoding="utf-8") as text_file:
                text_file.write(ar_content)
                
            print(f"    ✓ تم حفظ الجداول بنجاح: {text_filename}")
        else:
            print(f"    ⚠ تحذير: لم يتم العثور على جداول مقروءة في: {pdf_path.name}")

if __name__ == "__main__":
    process_health_safety_directory()
    print("="*50 + "\nاكتملت العملية! جميع الجداول الآن محفوظة كقواعد بيانات نصية نظيفة.")