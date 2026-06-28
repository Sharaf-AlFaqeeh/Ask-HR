import os
import io
import re
import numpy as np
from pathlib import Path
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import easyocr

# 1. إعداد المسارات الأساسية
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

TARGET_FOLDER_NAME = "سياسات الموارد البشريه"
SOURCE_FOLDER = BASE_DIR / "HSA_policies" / TARGET_FOLDER_NAME
OUTPUT_FOLDER = BASE_DIR / "extracted_texts"/"HR_POLICIES_v2" / TARGET_FOLDER_NAME

# 2. تحميل نماذج الذكاء الاصطناعي (السلاح الثقيل)
print("🚀 جاري تهيئة محرك الذكاء الاصطناعي (EasyOCR)... الرجاء الانتظار.")
reader = easyocr.Reader(['ar', 'en'], gpu=False, verbose=False)
print("✅ المحرك جاهز للمهمة!")

# 3. دوال المعالجة (بدون فصل اللغات)
def clean_text(text):
    """
    تنظيف النص الخفيف دون فصل اللغتين.
    """
    if not text:
        return ""
    
    # إزالة التطويل (ـ) وتنظيف المسافات الزائدة
    cleaned = str(text).replace('ـ', '') 
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def group_cells_into_rows(cells):
    """هندسة عكسية لبناء هيكل الجدول من الإحداثيات"""
    if not cells:
        return []
    cells.sort(key=lambda c: (c[1], c[0]))
    rows, current_row = [], []
    
    def get_center(c): return (c[1] + c[3]) / 2
    current_cy = get_center(cells[0])
    tolerance = 12 
    
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
        r.sort(key=lambda c: c[0], reverse=True) # ترتيب من اليمين لليسار
    return rows

def ai_read_image(pil_img):
    """قراءة الصورة باستخدام نموذج التعلم العميق"""
    img_array = np.array(pil_img)
    results = reader.readtext(img_array, detail=0, paragraph=True)
    return " ".join(results)

def process_complex_table(table, img, scale_x, scale_y):
    """قراءة الجداول خلية بخلية باستخدام الذكاء الاصطناعي ودمجها في جدول واحد"""
    md_lines = []
    grid = group_cells_into_rows(table.cells)
    max_cols = max(len(row) for row in grid) if grid else 0
    
    for i, row in enumerate(grid):
        row_data = []
        for cell in row:
            try:
                x0, top, x1, bottom = cell
                pad = 4 
                left = max(0, (x0 * scale_x) - pad)
                upper = max(0, (top * scale_y) - pad)
                right = min(img.width, (x1 * scale_x) + pad)
                lower = min(img.height, (bottom * scale_y) + pad)
                
                if right <= left or lower <= upper:
                    row_data.append(" ")
                    continue
                    
                cell_img = img.crop((left, upper, right, lower))
                text = ai_read_image(cell_img)
                cleaned = clean_text(text)
                
                row_data.append(cleaned if cleaned else " ")
                
            except Exception:
                row_data.append(" ")
                
        while len(row_data) < max_cols:
            row_data.append(" ")
            
        md_lines.append("| " + " | ".join(row_data) + " |")
        
        if i == 0:
            separator = "| " + " | ".join(["---"] * max_cols) + " |"
            md_lines.append(separator)
            
    return "\n".join(md_lines) + "\n\n"

# 4. المحرك الرئيسي لمعالجة الملفات
def extract_hr_policies_ai(pdf_path):
    full_text = ""
    
    try:
        plumber_pdf = pdfplumber.open(pdf_path)
        fitz_doc = fitz.open(pdf_path)
        
        for page_num, plumber_page in enumerate(plumber_pdf.pages):
            print(f"    ⏳ جاري مسح وقراءة الصفحة {page_num + 1} بالذكاء الاصطناعي...")
            
            hdr = f"--- بداية الصفحة ({page_num + 1}) ---\n\n"
            pg_text = ""
            
            fitz_page = fitz_doc.load_page(page_num)
            pix = fitz_page.get_pixmap(dpi=300, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            scale_x = img.width / plumber_page.width
            scale_y = img.height / plumber_page.height
            
            tables = plumber_page.find_tables()
            
            if tables:
                pg_text += "[جداول البيانات المكتشفة]:\n\n"
                
                img_masked = img.copy()
                draw = ImageDraw.Draw(img_masked)
                
                for idx, table in enumerate(tables):
                    pg_text += f"### [الجدول رقم {idx + 1}]\n"
                    
                    tbl_md = process_complex_table(table, img, scale_x, scale_y)
                    pg_text += tbl_md
                    
                    x0, top, x1, bottom = table.bbox
                    draw.rectangle(
                        [x0 * scale_x, top * scale_y, x1 * scale_x, bottom * scale_y], 
                        fill="white"
                    )
            else:
                img_masked = img 
                
            raw_text = ai_read_image(img_masked)
            plain_text = clean_text(raw_text)
            
            if plain_text.strip():
                pg_text += "[النصوص المصاحبة]:\n" + plain_text + "\n"
                
            full_text += hdr + pg_text + "\n"
            
        fitz_doc.close()
        
    except Exception as e:
        print(f"❌ حدث خطأ عام أثناء معالجة {pdf_path.name}: {e}")
        
    return full_text

# 5. التشغيل
def run_hr_ingestion():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FOLDER.exists():
        print(f"⚠️ تنبيه: المسار المصدر غير موجود: {SOURCE_FOLDER}")
        return

    print(f"🔥 بدء عملية الاستخراج الشاملة (AI-Vision) لمجلد: ({TARGET_FOLDER_NAME})...\n" + "="*60)

    pdf_files = list(SOURCE_FOLDER.glob("*.pdf"))
    if not pdf_files:
        print("لا توجد ملفات PDF هنا.")
        return

    for pdf_path in pdf_files:
        print(f"\n📂 جاري العمل على: {pdf_path.name}")
        
        content = extract_hr_policies_ai(pdf_path)
        
        if content.strip():
            filename = pdf_path.stem + ".txt"
            with open(OUTPUT_FOLDER / filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    ✅ تم حفظ المستند بسلامة ودقة عالية: {filename}")

if __name__ == "__main__":
    run_hr_ingestion()
    print("\n" + "="*60 + "\n🎯 تمت المهمة! تم قهر ملفات الموارد البشرية بأحدث التقنيات.")