# import os
# from pathlib import Path
# import pdfplumber
# import arabic_reshaper
# from bidi.algorithm import get_display

# # 1. تحديد المسارات الأساسية
# CURRENT_DIR = Path(__file__).resolve().parent
# BASE_DIR = CURRENT_DIR.parent

# TARGET_FOLDER_NAME = "سياسات التواصل الداخلي"

# SOURCE_FOLDER = BASE_DIR / "HSA_policies" / TARGET_FOLDER_NAME
# OUTPUT_FOLDER = BASE_DIR / "extracted_texts" / TARGET_FOLDER_NAME

# def extract_and_fix_text(pdf_path):
#     """
#     استخراج النصوص وإصلاحها باستخدام المكتبات الذكية.
#     هذه الطريقة آمنة هنا لأنه لا توجد جداول نخاف على انهيار تنسيقها.
#     """
#     full_content = ""
    
#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             for page_num, page in enumerate(pdf.pages):
#                 full_content += f"--- بداية الصفحة ({page_num + 1}) ---\n\n"
                
#                 # استخراج النص الخام من الصفحة
#                 raw_text = page.extract_text()
                
#                 if raw_text:
#                     # 1. إعادة تشكيل الحروف لترتبط ببعضها بشكل صحيح (يحل مشكلة التقطيع)
#                     reshaped_text = arabic_reshaper.reshape(raw_text)
                    
#                     # 2. ضبط الاتجاه ليقرأ من اليمين لليسار، مع الحفاظ على الإنجليزي (Yammer)
#                     bidi_output = get_display(reshaped_text)
#                     bidi_text = bidi_output.decode('utf-8') if isinstance(bidi_output, bytes) else bidi_output
                    
#                     full_content += bidi_text + "\n\n"
                    
#     except Exception as e:
#         print(f"حدث خطأ أثناء معالجة {pdf_path.name}: {e}")
        
#     return full_content

# def process_internal_comm_directory():
#     # إنشاء مجلد المخرجات
#     OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

#     if not SOURCE_FOLDER.exists():
#         print(f"تنبيه: المسار المصدر غير موجود: {SOURCE_FOLDER}")
#         return

#     print(f"بدء استخراج النصوص الصافية (بالمعالجة الذكية) لملفات: ({TARGET_FOLDER_NAME})...\n" + "="*50)

#     pdf_files = list(SOURCE_FOLDER.glob("*.pdf"))
#     if not pdf_files:
#         print("لا توجد ملفات PDF في هذا المجلد.")
#         return

#     for pdf_path in pdf_files:
#         print(f"جاري استخراج وإصلاح: {pdf_path.name}")
        
#         ar_content = extract_and_fix_text(pdf_path)
        
#         if ar_content.strip():
#             text_filename = pdf_path.stem + ".txt"
#             output_file_path = OUTPUT_FOLDER / text_filename
            
#             with open(output_file_path, "w", encoding="utf-8") as text_file:
#                 text_file.write(ar_content)
                
#             print(f"    ✓ تم الحفظ بنجاح: {text_filename}")
#         else:
#             print(f"    ⚠ تحذير: الملف فارغ: {pdf_path.name}")

# if __name__ == "__main__":
#     process_internal_comm_directory()
#     print("="*50 + "\nاكتملت العملية! يمكنك التحقق من الملف الآن.")