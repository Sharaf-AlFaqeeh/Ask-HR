# services/vector_db_service/preprocessing/cleaner.py
import re
import pdfplumber
from pathlib import Path
from typing import List, Dict, Any

def extract_text_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    يستخرج النص من ملف الـ PDF صفحة بصفحة مع الاحتفاظ برقم الصفحة.
    """
    pages_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                pages_data.append({
                    "page_number": i + 1,
                    "text": text
                })
    return pages_data

def correct_visual_arabic(text: str) -> str:
    """
    يكتشف ما إذا كان النص العربي المستخرج مكتوباً بترتيب بصري معكوس (Visual Order)
    ويقوم بتصحيحه عن طريق عكس الأحرف لكل سطر برمجياً.
    """
    if not text:
        return text
        
    # مؤشرات الكلمات المعكوسة الأكثر شيوعاً في العربية
    reversed_indicators = ["ىلع", "يف", "نم", "انم", "اذإ"]
    normal_indicators = ["على", "في", "من", "معنا", "إذا"]
    
    rev_count = sum(text.count(word) for word in reversed_indicators)
    norm_count = sum(text.count(word) for word in normal_indicators)
    
    # إذا كانت مؤشرات الكلمات المعكوسة أكثر، فغالباً النص بأكمله معكوس
    if rev_count > norm_count:
        lines = text.split("\n")
        corrected_lines = []
        for line in lines:
            # عكس السطر بالكامل
            corrected_line = line[::-1]
            # تبديل الأقواس المعكوسة نتيجة عكس السطر
            translation_table = str.maketrans("()[]<>{}", ")(][><}{")
            corrected_line = corrected_line.translate(translation_table)
            corrected_lines.append(corrected_line)
        return "\n".join(corrected_lines)
        
    return text

def clean_arabic_text(text: str) -> str:
    """
    تنظيف النص العربي من المسافات الزائدة، السطور المكسورة غير الصحيحة، والرموز الغريبة.
    """
    # 1. تصحيح الاتجاه البصري المعكوس للنصوص المستخرجة من بعض ملفات الـ PDF
    text = correct_visual_arabic(text)
    
    # 2. توحيد المسافات والسطور
    text = re.sub(r'\n+', '\n', text)  # دمج السطور المتعددة الفارغة
    text = re.sub(r' +', ' ', text)    # دمج المسافات الزائدة
    
    return text.strip()
