import os
import csv
import fitz  # PyMuPDF
from langdetect import detect, DetectorFactory
from tqdm import tqdm

# لضمان ثبات نتائج تحديد اللغة في كل مرة يتم فيها تشغيل الكود
DetectorFactory.seed = 0

def analyze_pdf(pdf_path):
    """
    يقوم بفحص ملف الـ PDF وتحديد حالته (نصي أم مصور) واللغة الغالبة عليه.
    """
    result = {
        "file_name": os.path.basename(pdf_path),
        "parent_folder": os.path.basename(os.path.dirname(pdf_path)),
        "total_pages": 0,
        "status": "Unknown",  # 'Digital' (نصي) or 'Scanned' (مصور)
        "language": "Unknown",
        "sample_text": ""
    }
    
    try:
        doc = fitz.open(pdf_path)
        result["total_pages"] = len(doc)
        
        # تجميع عينة نصية من أول 3 صفحات كحد أقصى للحكم على الملف
        sample_text = ""
        pages_to_check = min(3, len(doc))
        
        for i in range(pages_to_check):
            page = doc[i]
            sample_text += page.get_text().strip() + " "
            
        doc.close()
        
        # تنظيف النص المستخرج من المسافات الزائدة
        sample_text = " ".join(sample_text.split())
        
        # إذا كان النص المستخرج يحتوي على أكثر من 20 حرف، نعتبره ملفاً نصياً (Digital)
        if len(sample_text) > 20:
            result["status"] = "Digital (نصي قابل للنسخ)"
            result["sample_text"] = sample_text[:100] + "..."  # أخذ عينة بسيطة للعرض
            
            # محاولة التعرف على لغة النص المستخرج
            try:
                lang = detect(sample_text)
                if lang == 'ar':
                    result["language"] = "العربية (Arabic)"
                elif lang == 'en':
                    result["language"] = "الإنجليزية (English)"
                else:
                    result["language"] = f"أخرى ({lang})"
            except Exception:
                result["language"] = "تعذر تحديد اللغة تلقائياً"
        else:
            result["status"] = "Scanned (ملف مصور / يحتاج OCR)"
            result["language"] = "غير محدد (يتطلب معالجة صور)"
            result["sample_text"] = "لا يوجد نص مستخرج مباشرة"
            
    except Exception as e:
        result["status"] = "Error (ملف تالف أو محمي)"
        result["sample_text"] = str(e)
        
    return result

def main():
    # تحديد مسار المجلد الرئيسي للملفات بناءً على هيكلة المشروع الخاص بك
    # استخدام المسارات المطلقة (Absolute Paths) لتفادي أي مشاكل في بيئة التشغيل Windows
    base_dir = r"P:\____AI____\HSAGroup\AskHRPro\services\vector_db_service\HSA_policies"
    output_csv = "PDF_Analysis_Report.csv"
    
    if not os.path.exists(base_dir):
        print(f"خطأ: المسار التالي غير موجود، يرجى التأكد منه:\n{base_dir}")
        return
        
    print(f"بدء فحص وتصنيف ملفات الـ PDF في المجلد:\n{base_dir}\n")
    
    # تجميع كافة مسارات ملفات الـ PDF المتاحة في المجلدات الفرعية
    pdf_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
                
    if not pdf_files:
        print("لم يتم العثور على أي ملفات PDF في المسار المحدد.")
        return
        
    print(f"تم العثور على ({len(pdf_files)}) ملف PDF جاهز للفحص.\n")
    
    # فحص الملفات وحفظ النتائج
    report_data = []
    for pdf_path in tqdm(pdf_files, desc="جاري تحليل الملفات"):
        analysis = analyze_pdf(pdf_path)
        report_data.append(analysis)
        
    # كتابة النتائج في ملف CSV منظم في نفس مجلد تشغيل الاسكريبت
    headers = ["اسم الملف", "المجلد التابع له", "عدد الصفحات", "حالة الملف", "اللغة الأساسية", "عينة من النص المستخرج"]
    
    with open(output_csv, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for data in report_data:
            writer.writerow([
                data["file_name"],
                data["parent_folder"],
                data["total_pages"],
                data["status"],
                data["language"],
                data["sample_text"]
            ])
            
    print(f"\nتم الانتهاء بنجاح! تم حفظ التقرير الشامل في المسار الحالي باسم: {output_csv}")

if __name__ == "__main__":
    main()
