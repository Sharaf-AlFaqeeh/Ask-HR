import re
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# تحديد مسار محرك Tesseract الذي قمت بتثبيته للتو
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_and_clean_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    يستخرج النص من ملفات الـ PDF باستخدام تقنية التعرف البصري (OCR)
    """
    pages_data = []
    
    with fitz.open(pdf_path) as pdf:
        for i in range(len(pdf)):
            page = pdf[i]
            
            # 1. تحويل صفحة الـ PDF إلى صورة بدقة عالية
            zoom = 2.0 
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
           # 2. تحويل الصورة إلى صيغة متوافقة
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            
            # 3. استخراج النص بالذكاء الاصطناعي (مع تحديد اللغة العربية)
            raw_text = pytesseract.image_to_string(img, lang='ara')
            
            if raw_text and raw_text.strip():
                # 4. تنظيف النص الناتج
                cleaned_text = re.sub(r'\n+', '\n', raw_text)
                cleaned_text = re.sub(r' +', ' ', cleaned_text).strip()
                
                pages_data.append({
                    "page_number": i + 1,
                    "text": cleaned_text
                })
                
    return pages_data