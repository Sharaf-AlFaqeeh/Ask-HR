import os
import io
import re
import numpy as np
from pathlib import Path
import pdfplumber
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import easyocr

# ==========================================
# 1. إعداد المسارات الأساسية
# ==========================================
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent

TARGET_FOLDER_NAME = "سياسات الموارد البشريه"
SOURCE_FOLDER = BASE_DIR / "HSA_policies" / TARGET_FOLDER_NAME
OUTPUT_FOLDER = BASE_DIR / "extracted_texts" / TARGET_FOLDER_NAME

# ==========================================
# 2. تحميل نماذج الذكاء الاصطناعي (السلاح الثقيل)
# ==========================================
print("🚀 جاري تهيئة محرك الذكاء الاصطناعي (EasyOCR)... الرجاء الانتظار.")
# ملاحظة: إذا كان جهازك يحتوي على كرت شاشة Nvidia، قم بتغيير gpu=False إلى gpu=True لسرعة خيالية
reader = easyocr.Reader(['ar', 'en'], gpu=False, verbose=False)
print("✅ المحرك جاهز للمهمة!")

# ==========================================
# 3. دوال المعالجة والفصل الذكي
# ==========================================
def split_and_clean_text(text):
    """
    فصل النص إلى عربي وإنجليزي بذكاء.
    لا نستخدم فلتر العكس هنا لأن EasyOCR يخرج النص العربي سليماً 100%.
    """
    if not text:
        return "", ""
    
    ar_lines, en_lines = [], []
    
    for line in str(text).split('\n'):
        line = line.strip()
        if not line:
            continue
            
        has_ar = bool(re.search(r'[\u0600-\u06FF]', line))
        has_en = bool(re.search(r'[A-Za-z]', line))
        
        # الأرقام البحتة والرموز تذهب للملفين للحفاظ على دقة الرواتب والتواريخ
        if not has_ar and not has_en:
            ar_lines.append(line)
            en_lines.append(line)
            continue
            
        if has_en:
            # تنظيف الإنجليزي من أي شظايا عربية
            eng_only = re.sub(r'[^\x00-\x7F]+', ' ', line)
            eng_only = re.sub(r'\s+', ' ', eng_only).strip()
            if eng_only:
                en_lines.append(eng_only)
        
        if has_ar:
            # تنظيف العربي من الإنجليزي وإزالة التطويل
            ar_only = re.sub(r'[A-Za-z]+', ' ', line)
            ar_only = re.sub(r'\s+', ' ', ar_only).strip()
            ar_only = ar_only.replace('ـ', '') 
            if ar_only:
                ar_lines.append(ar_only)
                
    return '\n'.join(ar_lines), '\n'.join(en_lines)

def group_cells_into_rows(cells):
    """هندسة عكسية لبناء هيكل الجدول من الإحداثيات"""
    if not cells:
        return []
    cells.sort(key=lambda c: (c[1], c[0]))
    rows, current_row = [], []
    
    def get_center(c): return (c[1] + c[3]) / 2
    current_cy = get_center(cells[0])
    tolerance = 12 # تسامح أعلى قليلاً لاختلاف أحجام الخلايا في الموارد البشرية
    
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
    # paragraph=True يجمع الكلمات في جمل مترابطة بشكل ذكي
    results = reader.readtext(img_array, detail=0, paragraph=True)
    return " ".join(results)

def process_complex_table(table, img, scale_x, scale_y):
    """قراءة الجداول خلية بخلية باستخدام الذكاء الاصطناعي"""
    ar_md_lines, en_md_lines = [], []
    grid = group_cells_into_rows(table.cells)
    max_cols = max(len(row) for row in grid) if grid else 0
    
    for i, row in enumerate(grid):
        ar_row, en_row = [], []
        for cell in row:
            try:
                x0, top, x1, bottom = cell
                pad = 4 # هامش مريح
                left = max(0, (x0 * scale_x) - pad)
                upper = max(0, (top * scale_y) - pad)
                right = min(img.width, (x1 * scale_x) + pad)
                lower = min(img.height, (bottom * scale_y) + pad)
                
                if right <= left or lower <= upper:
                    ar_row.append(" "); en_row.append(" ")
                    continue
                    
                cell_img = img.crop((left, upper, right, lower))
                text = ai_read_image(cell_img)
                
                ar_text, en_text = split_and_clean_text(text)
                ar_row.append(ar_text if ar_text else " ")
                en_row.append(en_text if en_text else " ")
                
            except Exception:
                ar_row.append(" "); en_row.append(" ")
                
        while len(ar_row) < max_cols:
            ar_row.append(" "); en_row.append(" ")
            
        ar_md_lines.append("| " + " | ".join(ar_row) + " |")
        en_md_lines.append("| " + " | ".join(en_row) + " |")
        
        if i == 0:
            separator = "| " + " | ".join(["---"] * max_cols) + " |"
            ar_md_lines.append(separator)
            en_md_lines.append(separator)
            
    return "\n".join(ar_md_lines) + "\n\n", "\n".join(en_md_lines) + "\n\n"

# ==========================================
# 4. المحرك الرئيسي لمعالجة الملفات
# ==========================================
def extract_hr_policies_ai(pdf_path):
    full_ar, full_en = "", ""
    
    try:
        plumber_pdf = pdfplumber.open(pdf_path)
        fitz_doc = fitz.open(pdf_path)
        
        for page_num, plumber_page in enumerate(plumber_pdf.pages):
            print(f"    ⏳ جاري مسح وقراءة الصفحة {page_num + 1} بالذكاء الاصطناعي...")
            
            hdr_ar = f"--- بداية الصفحة ({page_num + 1}) ---\n\n"
            hdr_en = f"--- Page ({page_num + 1}) Start ---\n\n"
            pg_ar, pg_en = "", ""
            
            # التقاط الصورة بجودة فائقة
            fitz_page = fitz_doc.load_page(page_num)
            pix = fitz_page.get_pixmap(dpi=300, alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            scale_x = img.width / plumber_page.width
            scale_y = img.height / plumber_page.height
            
            tables = plumber_page.find_tables()
            
            # معالجة الجداول وطمسها من الصفحة
            if tables:
                pg_ar += "[جداول البيانات المكتشفة]:\n\n"
                pg_en += "[Discovered Data Tables]:\n\n"
                
                img_masked = img.copy()
                draw = ImageDraw.Draw(img_masked)
                
                for idx, table in enumerate(tables):
                    pg_ar += f"### [الجدول رقم {idx + 1}]\n"
                    pg_en += f"### [Table No. {idx + 1}]\n"
                    
                    ar_tbl, en_tbl = process_complex_table(table, img, scale_x, scale_y)
                    pg_ar += ar_tbl
                    pg_en += en_tbl
                    
                    # طمس منطقة الجدول لكي لا يقرأها الذكاء الاصطناعي مرة أخرى مع النصوص
                    x0, top, x1, bottom = table.bbox
                    draw.rectangle(
                        [x0 * scale_x, top * scale_y, x1 * scale_x, bottom * scale_y], 
                        fill="white"
                    )
            else:
                img_masked = img 
                
            # قراءة النصوص الحرة المتبقية في الصفحة
            raw_text = ai_read_image(img_masked)
            ar_plain, en_plain = split_and_clean_text(raw_text)
            
            if ar_plain.strip():
                pg_ar += "[النصوص المصاحبة]:\n" + ar_plain + "\n"
            if en_plain.strip():
                pg_en += "[Accompanying Text]:\n" + en_plain + "\n"
                
            full_ar += hdr_ar + pg_ar + "\n"
            full_en += hdr_en + pg_en + "\n"
            
        fitz_doc.close()
        
    except Exception as e:
        print(f"❌ حدث خطأ عام أثناء معالجة {pdf_path.name}: {e}")
        
    return full_ar, full_en

# ==========================================
# 5. التشغيل
# ==========================================
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
        
        ar_content, en_content = extract_hr_policies_ai(pdf_path)
        
        if ar_content.strip():
            ar_filename = pdf_path.stem + "_AR.txt"
            with open(OUTPUT_FOLDER / ar_filename, "w", encoding="utf-8") as f:
                f.write(ar_content)
            print(f"    ✅ تم حفظ النسخة العربية بسلامة ودقة عالية: {ar_filename}")
            
        if en_content.strip():
            en_filename = pdf_path.stem + "_EN.txt"
            with open(OUTPUT_FOLDER / en_filename, "w", encoding="utf-8") as f:
                f.write(en_content)
            print(f"    ✅ تم حفظ النسخة الإنجليزية بسلامة ودقة عالية: {en_filename}")

if __name__ == "__main__":
    run_hr_ingestion()
    print("\n" + "="*60 + "\n🎯 تمت المهمة! تم قهر ملفات الموارد البشرية بأحدث التقنيات.")