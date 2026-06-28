import os
import re
from pathlib import Path
import pdfplumber

# 1. تحديد المسارات الأساسية
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

TARGET_FOLDER_NAME = "سياسات الامتثال و الحوكمة"

SOURCE_FOLDER = BASE_DIR / "HSA_policies" / TARGET_FOLDER_NAME
OUTPUT_FOLDER = BASE_DIR / "extracted_texts" / TARGET_FOLDER_NAME

def split_and_clean_languages(text):
    """
    دالة تفصل النص بشكل صارم:
    - الإنجليزي: يبقى كما هو (بدون عكس) وتحذف منه أي حروف عربية تماماً.
    - العربي: يتم عكسه ليعود مقروءاً وتحذف منه الحروف الإنجليزية.
    - الأرقام/الرموز: تضاف لكلا اللغتين لضمان سلامة الجداول.
    """
    if not text:
        return "", ""
    
    ar_lines = []
    en_lines = []
    
    for line in str(text).split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # فحص محتوى السطر
        has_ar = bool(re.search(r'[\u0600-\u06FF]', line))
        has_en = bool(re.search(r'[A-Za-z]', line))
        
        # --- حالة الأرقام والرموز فقط (تضاف للملفين) ---
        if not has_ar and not has_en:
            ar_lines.append(line)
            en_lines.append(line)
            continue
            
        # --- 1. معالجة النص الإنجليزي (بدون عكس) ---
        if has_en:
            # الإبقاء فقط على الحروف اللاتينية الأساسية والأرقام والرموز (حذف كامل للعربي)
            eng_only = re.sub(r'[^\x00-\x7F]+', ' ', line)
            # تنظيف المسافات المزدوجة
            eng_only = re.sub(r'\s+', ' ', eng_only).strip()
            
            if eng_only:
                en_lines.append(eng_only)
        
        # --- 2. معالجة النص العربي (مع العكس) ---
        if has_ar:
            # حذف الحروف الإنجليزية
            ar_only = re.sub(r'[A-Za-z]+', ' ', line)
            ar_only = re.sub(r'\s+', ' ', ar_only).strip()
            
            # عكس النص العربي
            ar_reversed = ar_only[::-1]
            
            # تنظيف الكشيدة والأقواس
            ar_reversed = ar_reversed.replace('ـ', '')
            ar_reversed = ar_reversed.replace(')', '\x00').replace('(', ')').replace('\x00', '(')
            ar_reversed = ar_reversed.replace(']', '\x00').replace('[', ']').replace('\x00', '[')
            
            if ar_reversed.strip():
                ar_lines.append(ar_reversed.strip())
                
    return '\n'.join(ar_lines), '\n'.join(en_lines)

def format_dual_tables(table):
    """تحويل المصفوفة إلى جدولين منفصلين (عربي وإنجليزي)"""
    if not table:
        return "", ""
    
    ar_markdown_lines = []
    en_markdown_lines = []
    
    for i, row in enumerate(table):
        ar_row = []
        en_row = []
        
        for cell in row:
            ar_cell, en_cell = split_and_clean_languages(cell)
            ar_row.append(ar_cell.replace('\n', ' ').strip() if ar_cell else " ")
            en_row.append(en_cell.replace('\n', ' ').strip() if en_cell else " ")
            
        ar_markdown_lines.append("| " + " | ".join(ar_row) + " |")
        en_markdown_lines.append("| " + " | ".join(en_row) + " |")
        
        if i == 0:
            ar_markdown_lines.append("| " + " | ".join(["---"] * len(row)) + " |")
            en_markdown_lines.append("| " + " | ".join(["---"] * len(row)) + " |")
            
    return "\n".join(ar_markdown_lines) + "\n", "\n".join(en_markdown_lines) + "\n"

def extract_dual_content(pdf_path):
    """توليد محتوى منفصل للغتين من كامل المستند"""
    full_ar_content = ""
    full_en_content = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                header_ar = f"--- بداية الصفحة ({page_num + 1}) ---\n\n"
                header_en = f"--- Page ({page_num + 1}) Start ---\n\n"
                
                page_ar_text = ""
                page_en_text = ""
                
                if page_num == 0: 
                    tables = page.extract_tables()
                    if tables:
                        page_ar_text += "[تم العثور على جدول في هذه الصفحة]:\n"
                        page_en_text += "[Table found on this page]:\n"
                        
                        for table in tables:
                            ar_table, en_table = format_dual_tables(table)
                            page_ar_text += ar_table + "\n"
                            page_en_text += en_table + "\n"
                        
                        text = page.extract_text()
                        if text:
                            ar_text, en_text = split_and_clean_languages(text)
                            if ar_text.strip():
                                page_ar_text += "\n[النصوص المصاحبة في الصفحة الأولى]:\n" + ar_text + "\n"
                            if en_text.strip():
                                page_en_text += "\n[Text accompanying the table]:\n" + en_text + "\n"
                            
                        full_ar_content += header_ar + page_ar_text + "\n"
                        full_en_content += header_en + page_en_text + "\n"
                        continue 
                
                text = page.extract_text()
                if text:
                    ar_text, en_text = split_and_clean_languages(text)
                    if ar_text.strip():
                        page_ar_text += ar_text + "\n"
                    if en_text.strip():
                        page_en_text += en_text + "\n"
                    
                full_ar_content += header_ar + page_ar_text + "\n"
                full_en_content += header_en + page_en_text + "\n"
                
    except Exception as e:
        print(f"حدث خطأ أثناء معالجة {pdf_path.name}: {e}")
        
    return full_ar_content, full_en_content

def process_compliance_directory():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FOLDER.exists():
        print(f"تنبيه: المسار المصدر غير موجود: {SOURCE_FOLDER}")
        return

    print(f"بدء الفصل الثنائي الصارم لملفات: ({TARGET_FOLDER_NAME})...\n" + "="*50)

    pdf_files = list(SOURCE_FOLDER.glob("*.pdf"))
    if not pdf_files:
        print("لا توجد ملفات PDF في هذا المجلد.")
        return

    for pdf_path in pdf_files:
        print(f"جاري استخراج وفصل: {pdf_path.name}")
        
        ar_content, en_content = extract_dual_content(pdf_path)
        
        # حفظ الملف العربي
        if ar_content.strip():
            ar_filename = pdf_path.stem + "_AR.txt"
            ar_file_path = OUTPUT_FOLDER / ar_filename
            with open(ar_file_path, "w", encoding="utf-8") as ar_file:
                ar_file.write(ar_content)
            print(f"    ✓ تم حفظ النسخة العربية: {ar_filename}")
            
        # حفظ الملف الإنجليزي
        if en_content.strip():
            en_filename = pdf_path.stem + "_EN.txt"
            en_file_path = OUTPUT_FOLDER / en_filename
            with open(en_file_path, "w", encoding="utf-8") as en_file:
                en_file.write(en_content)
            print(f"    ✓ تم حفظ النسخة الإنجليزية: {en_filename}")
            
        print("-" * 30)

if __name__ == "__main__":
    process_compliance_directory()
    print("="*50 + "\nاكتملت عملية الفصل الثنائي بنجاح!")