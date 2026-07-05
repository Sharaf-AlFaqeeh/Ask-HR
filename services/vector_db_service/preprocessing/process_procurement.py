import os
import io
import re
import numpy as np
from pathlib import Path
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import easyocr

# 1. تحديد المسارات
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

TARGET_FOLDER_NAME = "سياسات المشتريات"
SOURCE_FOLDER = BASE_DIR / "HSA_policies" / TARGET_FOLDER_NAME
OUTPUT_FOLDER = BASE_DIR / "extracted_texts" / TARGET_FOLDER_NAME

# 2. تحميل نموذج الذكاء الاصطناعي (يتم تحميله مرة واحدة لتسريع العملية)
print("جاري تحميل نماذج الذكاء الاصطناعي (EasyOCR)... الرجاء الانتظار قليلاً.")
# gpu=False لضمان عمله على جميع الأجهزة، إذا كان لديك كرت شاشة Nvidia يمكنك جعلها True
reader = easyocr.Reader(['ar', 'en'], gpu=False, verbose=False)

def split_and_clean_ocr_text(text):
    """تنظيف وفصل النص الناتج من EasyOCR"""
    if not text:
        return "", ""
    
    ar_lines = []
    en_lines = []
    
    for line in str(text).split('\n'):
        line = line.strip()
        if not line:
            continue
            
        has_ar = bool(re.search(r'[\u0600-\u06FF]', line))
        has_en = bool(re.search(r'[A-Za-z]', line))
        
        if not has_ar and not has_en:
            ar_lines.append(line)
            en_lines.append(line)
            continue
            
        if has_en:
            eng_only = re.sub(r'[^\x00-\x7F]+', ' ', line)
            eng_only = re.sub(r'\s+', ' ', eng_only).strip()
            if eng_only:
                en_lines.append(eng_only)
        
        if has_ar:
            ar_only = re.sub(r'[A-Za-z]+', ' ', line)
            ar_only = re.sub(r'\s+', ' ', ar_only).strip()
            ar_only = ar_only.replace('ـ', '') 
            if ar_only:
                ar_lines.append(ar_only)
                
    return '\n'.join(ar_lines), '\n'.join(en_lines)

def group_cells_into_rows(cells):
    """هندسة الجداول"""
    if not cells:
        return []
    cells.sort(key=lambda c: (c[1], c[0]))
    rows = []
    current_row = []
    def get_center(c): return (c[1] + c[3]) / 2
    current_cy = get_center(cells[0])
    tolerance = 10 
    
    for cell in cells:
        cy = get_center(cell)
        if abs(cy - current_cy) <= tolerance:
            current_row.append(cell)
        else:
            rows.append(current_row)
            current_row = [cell]
            current_cy = cy
    if current_row:
        rows.append(current_row)
        
    for r in rows:
        r.sort(key=lambda c: c[0], reverse=True) 
    return rows

def extract_text_with_easyocr(pil_img):
    """دالة وسيطة لتحويل صورة PIL إلى Numpy ثم قراءتها بـ EasyOCR"""
    # تحويل الصورة إلى مصفوفة رقمية يفهمها EasyOCR
    img_array = np.array(pil_img)
    
    # القراءة (detail=0 تُرجع النص فقط بدون إحداثيات البكسلات)
    results = reader.readtext(img_array, detail=0, paragraph=True)
    return " ".join(results)

def process_table_with_easyocr(table, img, scale_x, scale_y):
    ar_markdown_lines = []
    en_markdown_lines = []
    
    grid = group_cells_into_rows(table.cells)
    max_cols = max(len(row) for row in grid) if grid else 0
    
    for i, row in enumerate(grid):
        ar_row, en_row = [], []
        for cell in row:
            try:
                x0, top, x1, bottom = cell
                
                pad = 3
                left = max(0, (x0 * scale_x) - pad)
                upper = max(0, (top * scale_y) - pad)
                right = min(img.width, (x1 * scale_x) + pad)
                lower = min(img.height, (bottom * scale_y) + pad)
                
                if right <= left or lower <= upper:
                    ar_row.append(" "); en_row.append(" ")
                    continue
                    
                cell_img = img.crop((left, upper, right, lower))
                
                # لم نعد بحاجة للتكبير العنيف، EasyOCR ذكي جداً
                
                # قراءة الخلية بالذكاء الاصطناعي
                text = extract_text_with_easyocr(cell_img)
                
                ar_text, en_text = split_and_clean_ocr_text(text)
                ar_row.append(ar_text if ar_text else " ")
                en_row.append(en_text if en_text else " ")
                
            except Exception:
                ar_row.append(" "); en_row.append(" ")
                
        while len(ar_row) < max_cols:
            ar_row.append(" "); en_row.append(" ")
            
        ar_markdown_lines.append("| " + " | ".join(ar_row) + " |")
        en_markdown_lines.append("| " + " | ".join(en_row) + " |")
        
        if i == 0:
            separator = "| " + " | ".join(["---"] * max_cols) + " |"
            ar_markdown_lines.append(separator)
            en_markdown_lines.append(separator)
            
    return "\n".join(ar_markdown_lines) + "\n\n", "\n".join(en_markdown_lines) + "\n\n"

def extract_procurement_easyocr(pdf_path):
    full_ar_content = ""
    full_en_content = ""
    
    try:
        plumber_pdf = pdfplumber.open(pdf_path)
        fitz_doc = fitz.open(pdf_path)
        
        for page_num, plumber_page in enumerate(plumber_pdf.pages):
            print(f"    - جاري تحليل الصفحة {page_num + 1} بواسطة EasyOCR (قد يستغرق دقائق)...")
            
            header_ar = f"--- بداية الصفحة ({page_num + 1}) ---\n\n"
            header_en = f"--- Page ({page_num + 1}) Start ---\n\n"
            page_ar_text, page_en_text = "", ""
            
            fitz_page = fitz_doc.load_page(page_num)
            pix = fitz_page.get_pixmap(dpi=300, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            scale_x = img.width / plumber_page.width
            scale_y = img.height / plumber_page.height
            
            tables = plumber_page.find_tables()
            
            if tables:
                page_ar_text += "\n"
                page_en_text += "[Discovered Tables]:\n"
                
                img_masked = img.copy()
                draw = ImageDraw.Draw(img_masked)
                
                for idx, table in enumerate(tables):
                    ar_tbl, en_tbl = process_table_with_easyocr(table, img, scale_x, scale_y)
                    page_ar_text += ar_tbl
                    page_en_text += en_tbl
                    
                    x0, top, x1, bottom = table.bbox
                    draw.rectangle(
                        [x0 * scale_x, top * scale_y, x1 * scale_x, bottom * scale_y], 
                        fill="white"
                    )
            else:
                img_masked = img 
                
            # قراءة النصوص العادية في باقي الصفحة
            raw_page_text = extract_text_with_easyocr(img_masked)
            ar_plain, en_plain = split_and_clean_ocr_text(raw_page_text)
            
            if ar_plain.strip():
                page_ar_text += "[النصوص المصاحبة]:\n" + ar_plain + "\n"
            if en_plain.strip():
                page_en_text += "[Accompanying Text]:\n" + en_plain + "\n"
                
            full_ar_content += header_ar + page_ar_text + "\n"
            full_en_content += header_en + page_en_text + "\n"
            
        fitz_doc.close()
        
    except Exception as e:
        print(f"حدث خطأ عام أثناء معالجة {pdf_path.name}: {e}")
        
    return full_ar_content, full_en_content

def process_procurement_directory():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FOLDER.exists():
        print(f"تنبيه: المسار المصدر غير موجود.")
        return

    print(f"بدء الاستخراج المتقدم (EasyOCR) لملفات: ({TARGET_FOLDER_NAME})...\n" + "="*50)

    pdf_files = list(SOURCE_FOLDER.glob("*.pdf"))
    if not pdf_files:
        return

    for pdf_path in pdf_files:
        print(f"جاري العمل على: {pdf_path.name}")
        
        ar_content, en_content = extract_procurement_easyocr(pdf_path)
        
        if ar_content.strip():
            ar_filename = pdf_path.stem + "_AR.txt"
            ar_file_path = OUTPUT_FOLDER / ar_filename
            with open(ar_file_path, "w", encoding="utf-8") as ar_file:
                ar_file.write(ar_content)
            print(f"    ✓ تم حفظ النسخة العربية: {ar_filename}")
            
        if en_content.strip():
            en_filename = pdf_path.stem + "_EN.txt"
            en_file_path = OUTPUT_FOLDER / en_filename
            with open(en_file_path, "w", encoding="utf-8") as en_file:
                en_file.write(en_content)
            print(f"    ✓ تم حفظ النسخة الإنجليزية: {en_filename}")

if __name__ == "__main__":
    process_procurement_directory()
    print("="*50 + "\nتم القضاء على الهلوسة بنجاح!")