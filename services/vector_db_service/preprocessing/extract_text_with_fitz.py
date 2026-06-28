import os
from pathlib import Path
import pdfplumber

# 1. تحديد المسارات الأساسية بشكل ديناميكي
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

SOURCE_FOLDER = BASE_DIR / "HSA_policies" / "تكنولوجيا المعلومات"
OUTPUT_FOLDER = BASE_DIR / "extracted_texts" / "تكنولوجيا المعلومات"

def simple_reverse_filter(text):
    """فلتر بسيط يعكس النص ليعود لشكله الصحيح بناءً على اقتراحك"""
    if not text:
        return " "
    
    # تقسيم النص إلى أسطر وعكس كل سطر على حدة للحفاظ على ترتيب الأسطر عمودياً
    lines = str(text).split('\n')
    reversed_lines = [line[::-1] for line in lines]
    return '\n'.join(reversed_lines)

def format_table_to_markdown(table):
    """تحويل المصفوفة إلى جدول مقروء مع تطبيق فلتر العكس على كل خلية"""
    if not table:
        return ""
    
    markdown_lines = []
    for i, row in enumerate(table):
        # تطبيق الفلتر البسيط على كل خلية
        cleaned_row = [simple_reverse_filter(cell).strip() if cell else " " for cell in row]
        
        # رص عناصر الصف يفصل بينها |
        line = "| " + " | ".join(cleaned_row) + " |"
        markdown_lines.append(line)
        
        # إضافة خط فاصل بعد الهيدر (الصف الأول)
        if i == 0:
            separator = "| " + " | ".join(["---"] * len(row)) + " |"
            markdown_lines.append(separator)
            
    return "\n".join(markdown_lines) + "\n"

def extract_smart_content(pdf_path):
    """استخراج النصوص والجداول وتمريرها عبر فلتر العكس"""
    full_content = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                full_content += f"--- بداية الصفحة ({page_num + 1}) ---\n\n"
                
                # التعامل مع الجداول في الصفحة الأولى
                if page_num == 0: 
                    tables = page.extract_tables()
                    if tables:
                        full_content += "[تم العثور على جدول في هذه الصفحة]:\n"
                        for table in tables:
                            full_content += format_table_to_markdown(table)
                            full_content += "\n"
                        
                        # استخراج النص المتبقي وتمريره للفلتر
                        text = page.extract_text()
                        if text:
                            full_content += "\n[النصوص المصاحبة في الصفحة الأولى]:\n"
                            full_content += simple_reverse_filter(text) + "\n"
                        continue 
                
                # للصفحات الأخرى
                text = page.extract_text()
                if text:
                    full_content += simple_reverse_filter(text) + "\n"
                    
                full_content += "\n"
    except Exception as e:
        print(f"حدث خطأ أثناء معالجة {pdf_path.name}: {e}")
        
    return full_content

def process_directory():
    # إنشاء مجلد المخرجات إذا لم يكن موجوداً
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FOLDER.exists():
        print(f"تنبيه: المسار المصدر غير موجود: {SOURCE_FOLDER}")
        return

    print(f"بدء المعالجة مع تطبيق الفلتر العكسي...\n" + "="*50)

    pdf_files = list(SOURCE_FOLDER.glob("*.pdf"))
    if not pdf_files:
        print("لا توجد ملفات PDF في هذا المجلد.")
        return

    for pdf_path in pdf_files:
        print(f"جاري استخراج: {pdf_path.name}")
        
        smart_text = extract_smart_content(pdf_path)
        
        if smart_text.strip():
            text_filename = pdf_path.stem + ".txt"
            output_file_path = OUTPUT_FOLDER / text_filename
            
            with open(output_file_path, "w", encoding="utf-8") as text_file:
                text_file.write(smart_text)
                
            print(f"✓ تم الحفظ بنجاح في: {output_file_path.name}\n")
        else:
            print(f"⚠ تحذير: الملف فارغ أو تعذر كشطه: {pdf_path.name}\n")

if __name__ == "__main__":
    process_directory()
    print("="*50 + "\nاكتملت العملية!")