import os
import tiktoken
from pathlib import Path

# 1. الإعدادات والمسارات
BASE_DIR = r"P:\____AI____\HSAGroup\AskHRPro\services\vector_db_service\extracted_texts"
TOKEN_LIMIT = 2000 # الحد الأقصى المسموح به للنموذج

# تهيئة الـ Tokenizer (استخدام معيار cl100k_base ليكون قريباً جداً من أداء معظم النماذج الحديثة)
try:
    tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception as e:
    print("❌ يرجى تثبيت مكتبة tiktoken عبر الأمر: pip install tiktoken")
    exit()

def get_token_count(text: str) -> int:
    """دالة لحساب عدد التوكنز في النص"""
    return len(tokenizer.encode(text))

# 2. دورة الفحص والتحليل
def main():
    print(f"🔍 جاري فحص الملفات النصية في المسار: {BASE_DIR}\n")
    print("-" * 50)
    
    total_files = 0
    files_over_limit = 0
    
    longest_file = {"name": "", "tokens": 0}
    shortest_file = {"name": "", "tokens": float('inf')}
    
    # البحث في كل المجلدات الفرعية عن ملفات txt
    txt_files = list(Path(BASE_DIR).rglob("*.txt"))
    
    if not txt_files:
        print("⚠️ لم يتم العثور على أي ملفات نصية في المسار المحدد.")
        return

    # المرور على جميع الملفات
    for txt_file in txt_files:
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                text_content = f.read()
                
            # حساب التوكنز
            tokens = get_token_count(text_content)
            total_files += 1
            
            # طباعة اسم الملف (مع اسم المجلد التابع له) وعدد التوكنز
            file_rel_path = f"{txt_file.parent.name}/{txt_file.name}"
            
            # تمييز الملفات التي تتجاوز الحد بصرياً
            if tokens > TOKEN_LIMIT:
                print(f"🔴 [تجاوز الحد] {file_rel_path} -> {tokens} توكن")
                files_over_limit += 1
            else:
                print(f"🟢 [سليم] {file_rel_path} -> {tokens} توكن")
            
            # تحديث إحصائيات أطول وأقصر ملف
            if tokens > longest_file["tokens"]:
                longest_file = {"name": file_rel_path, "tokens": tokens}
                
            if tokens < shortest_file["tokens"]:
                shortest_file = {"name": file_rel_path, "tokens": tokens}
                
        except Exception as e:
            print(f"⚠️ خطأ في قراءة الملف {txt_file.name}: {str(e)}")

        # 3. طباعة التقرير النهائي
        print("\n" + "=" * 50)
    print("📊 التقرير النهائي لتحليل التوكنز")
    print("=" * 50)
    print(f"📁 إجمالي الملفات المفحوصة: {total_files}")
    print(f"📈 الحد الأقصى المسموح للتوكن: {TOKEN_LIMIT}")
    print(f"⚠️ عدد الملفات التي تجاوزت الحد: {files_over_limit}")
    print("-" * 50)
    
    if total_files > 0:
        print(f"🥇 أطول ملف: {longest_file['name']} ({longest_file['tokens']} توكن)")
        print(f"🤏 أقصر ملف: {shortest_file['name']} ({shortest_file['tokens']} توكن)")
    print("=" * 50)

if __name__ == "__main__":
    main()