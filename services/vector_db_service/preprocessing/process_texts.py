import os
import sys
import re
from pathlib import Path

# Fix Windows console encoding issues
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Paths
BASE_DIR = Path(r"P:\____AI____\HSAGroup\AskHRPro\services\vector_db_service")
INPUT_DIR = BASE_DIR / "extracted_texts"
OUTPUT_DIR = BASE_DIR / "structured_texts_md"

# Define the 37 target documents and their sources
TARGET_FILES = [
    # 1. تكنولوجيا المعلومات
    ("تكنولوجيا المعلومات", "سياسة استخدام البريد الالكترونى.txt", INPUT_DIR / "تكنولوجيا المعلومات" / "سياسة استخدام البريد الالكترونى.txt"),
    ("تكنولوجيا المعلومات", "سياسة الاستخدام الآمن للانترنت.txt", INPUT_DIR / "تكنولوجيا المعلومات" / "سياسة الاستخدام الآمن للانترنت.txt"),
    ("تكنولوجيا المعلومات", "سياسة الاستخدام الامن لاجهزة الحاسب الشخصي.txt", INPUT_DIR / "تكنولوجيا المعلومات" / "سياسة الاستخدام الامن لاجهزة الحاسب الشخصي.txt"),
    ("تكنولوجيا المعلومات", "سياسة التحكم فى امن تكنولوجيا المعلومات.txt", INPUT_DIR / "تكنولوجيا المعلومات" / "سياسة التحكم فى امن تكنولوجيا المعلومات.txt"),
    
    # 2. سياسات الاتصال المؤسسي
    ("سياسات الاتصال المؤسسي", "سياسة وسائل التواصل الاجتماعي.txt", INPUT_DIR / "سياسات الاتصال المؤسسي" / "سياسة وسائل التواصل الاجتماعي.txt"),
    
    # 3. سياسات التواصل الداخلي
    ("سياسات التواصل الداخلي", "السياسة الخاصة بمنصة التواصل الاجتماعي الداخلي Yammer.txt", INPUT_DIR / "سياسات التواصل الداخلي" / "السياسة الخاصة بمنصة التواصل الاجتماعي الداخلي Yammer.txt"),
    
    # 4. سياسات الصحة والسلامة المهنية
    ("سياسات الصحة والسلامة المهنية", "إجراءات إثبات وتطبيق العقوبة لمخالفات السلامة المهنية.txt", INPUT_DIR / "سياسات الصحة والسلامة المهنية" / "إجراءات إثبات وتطبيق العقوبة لمخالفات السلامة المهنية.txt"),
    ("سياسات الصحة والسلامة المهنية", "لائحة المخالفات والجزاءات السلامة المهنية.txt", INPUT_DIR / "سياسات الصحة والسلامة المهنية" / "لائحة المخالفات والجزاءات السلامة المهنية.txt"),
    
    # 5. سياسات المالية
    ("سياسات المالية", "سياسة الأصول الثابتة، المنشآت والمعدات.txt", INPUT_DIR / "سياسات المالية" / "سياسة الأصول الثابتة، المنشآت والمعدات_AR.txt"),
    
    # 6. سياسات المشتريات
    ("سياسات المشتريات", "سياسة المشتريات.txt", INPUT_DIR / "سياسات المشتريات" / "سياسة المشتريات_AR.txt"),
    
    # 7. سياسات الامتثال و الحوكمة
    ("سياسات الامتثال و الحوكمة", "سياسة الابلاغ.txt", INPUT_DIR / "سياسات الامتثال و الحوكمة" / "سياسة الابلاغ_AR.txt"),
    ("سياسات الامتثال و الحوكمة", "سياسة التجارة الدولية والعقوبات المالية.txt", INPUT_DIR / "سياسات الامتثال و الحوكمة" / "سياسة التجارة الدولية والعقوبات المالية_AR.txt"),
    ("سياسات الامتثال و الحوكمة", "سياسة التحقيقات.txt", INPUT_DIR / "سياسات الامتثال و الحوكمة" / "سياسة التحقيقات_AR.txt"),
    ("سياسات الامتثال و الحوكمة", "سياسة إدارة مخاطر الامتثال لشركاء الأعمال.txt", INPUT_DIR / "سياسات الامتثال و الحوكمة" / "سياسة إدارة مخاطر الامتثال لشركاء الأعمال_AR.txt"),
    ("سياسات الامتثال و الحوكمة", "سياسة تعارض المصالح.txt", INPUT_DIR / "سياسات الامتثال و الحوكمة" / "سياسة تعارض المصالح_AR.txt"),
    ("سياسات الامتثال و الحوكمة", "سياسة حوكمة البيانات.txt", INPUT_DIR / "سياسات الامتثال و الحوكمة" / "سياسة حوكمة البيانات_AR.txt"),
    ("سياسات الامتثال و الحوكمة", "سياسة مكافحة الرشوة والفساد.txt", INPUT_DIR / "سياسات الامتثال و الحوكمة" / "سياسة مكافحة الرشوة والفساد_AR.txt"),
    ("سياسات الامتثال و الحوكمة", "سياسة مكافحة غسل الأموال ومكافحة تمويل الإرهاب.txt", INPUT_DIR / "سياسات الامتثال و الحوكمة" / "سياسة مكافحة غسل الأموال ومكافحة تمويل الإرهاب_AR.txt"),
    ("سياسات الامتثال و الحوكمة", "قواعد السلوك المهني لشركاء الأعمال.txt", INPUT_DIR / "سياسات الامتثال و الحوكمة" / "قواعد السلوك المهني لشركاء الأعمال_AR.txt"),
    
    # 8. سياسات الموارد البشريه (from HR_POLICIES_v2)
    ("سياسات الموارد البشريه", "سياسة استقطاب المواهب 2025.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة استقطاب المواهب 2025.txt"),
    ("سياسات الموارد البشريه", "سياسة الترقيات.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة الترقيات.txt"),
    ("سياسات الموارد البشريه", "سياسة التسهيلات الماليه2025.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة التسهيلات الماليه2025.txt"),
    ("سياسات الموارد البشريه", "سياسة التعلم والتطوير.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة التعلم والتطوير.txt"),
    ("سياسات الموارد البشريه", "سياسة التواصل الاجتماعي.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة التواصل الاجتماعي.txt"),
    ("سياسات الموارد البشريه", "سياسة التوظيف الداخلي 2026.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة التوظيف الداخلي 2026.txt"),
    ("سياسات الموارد البشريه", "سياسة الحوافز والمكافات2025.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة الحوافز والمكافات2025.txt"),
    ("سياسات الموارد البشريه", "سياسة الخصوصية.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة الخصوصية.txt"),
    ("سياسات الموارد البشريه", "سياسة السفر وبدل المواصلات 2026.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة السفر وبدل المواصلات 2026.txt"),
    ("سياسات الموارد البشريه", "سياسة الضمانات للموظفين 2026.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة الضمانات للموظفين 2026.txt"),
    ("سياسات الموارد البشريه", "سياسة إنتهاء خدمات الموظفين 2026.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة إنتهاء خدمات الموظفين 2026.txt"),
    ("سياسات الموارد البشريه", "سياسة تصنيف القوى العاملة.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة تصنيف القوى العاملة.txt"),
    ("سياسات الموارد البشريه", "سياسة تنظيم أوقات العمل والإجازات 2026.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة تنظيم أوقات العمل والإجازات 2026.txt"),
    ("سياسات الموارد البشريه", "سياسة حقوق الانسان و إدارة شكاوى الموظفين 2026.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة حقوق الانسان و إدارة شكاوى الموظفين 2026.txt"),
    ("سياسات الموارد البشريه", "سياسة دعم التعليم.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة دعم التعليم.txt"),
    ("سياسات الموارد البشريه", "سياسة صندوق التكافل للمساعدات الاجتماعية2025.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة صندوق التكافل للمساعدات الاجتماعية2025.txt"),
    ("سياسات الموارد البشريه", "سياسة نقل الموظفين 2026.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "سياسة نقل الموظفين 2026.txt"),
    ("سياسات الموارد البشريه", "لائحة المخالفات والجزاءات.txt", INPUT_DIR / "HR_POLICIES_v2" / "سياسات الموارد البشريه" / "لائحة المخالفات والجزاءات.txt"),
]

# Safety policy specific decryption map for standard column headers & generic terms
SAFETY_POLICY_GARBLED_MAP = {
    "الجازء المقرر": "الجزاء المقرر",
    "مرة اربع ة": "مرة رابعة",
    "مرة ثالث ة": "مرة ثالثة",
    "مرة ثاني ة": "مرة ثانية",
    "مرة أول ى": "مرة أولى",
    "فصلسمنسس تشعمسل": "فصل من العمل",
    "فصلسمنستشعمل": "فصل من العمل",
    "خمس سأي سا": "خمسة أيام",
    "خمس سس أي اسس": "خمسة أيام",
    "خمس سأي اسس": "خمسة أيام",
    "ثالث سأي اسس": "ثلاثة أيام",
    "ثالث سأي ا": "ثلاثة أيام",
    "ثلاث سأي اسس": "ثلاثة أيام",
    "يرم سن": "يومين",
    "يرم نسس": "يومين",
    "يرم نس": "يومين",
    "يرم نسس س": "يومين",
    "يوم سن": "يومين",
    "نصفسيرسا": "نصف يوم",
    "يرا": "يوم",
    "يرم": "يوم",
    "يراس": "يوم",
    "إنذت سلو ب سس": "إنذار كتابي",
    "إنذت سس كو ب سس": "إنذار كتابي",
    "ش،تسنظرسس": "لفت نظر",
    "معستاملستشوك ش سف": "مع استكمال الإجراءات",
    "معستاملستشوك ش فس": "مع استكمال الإجراءات",
    "معستاملستشوك ش فسس": "مع استكمال الإجراءات",
    "معستاملستشوك ش سف معستاملستشوك ش سف": "مع استكمال الإجراءات",
    "أس بع سسأي سا": "أربعة أيام",
    "أ بع سأي سا": "أربعة أيام",
    "تاملستشاس ةس ك م": "تحمل التكلفة كاملة",
    "%س75تامل منستشاس ةس": "تحمل 75% من التكلفة",
    "%س50تامل منستشاس ةس": "تحمل 50% من التكلفة",
    "%س25تامل منستشاس ةس": "تحمل 25% من التكلفة",
    "تاملستك ش فست ال ستشن تجسعنستشع بسإنس ت": "تحمل تكلفة الكشف والاتصال الناتج عن اللعب بإنذار الحريق",
    "تاملستك ش فست ال ستشن تجسعنستشع بسإنس ت  س": "تحمل تكلفة الكشف والاتصال الناتج عن اللعب بإنذار الحريق",
    "تاملستك ش فست": "تحمل تكلفة الكشف والاتصال",
}

def clean_safety_policy_garbled(text: str) -> str:
    # Split the text into lines and process each table row
    lines = text.split('\n')
    new_lines = []
    
    for line in lines:
        if '|' in line:
            # It's a table row
            cells = line.split('|')
            cleaned_cells = []
            for cell in cells:
                c = cell.strip()
                
                # Check for replacements based on key substrings
                # 133
                if "استشارتت" in c or "تشواذيري" in c or "dddddddd" in c or "استخددد" in c:
                    c = "عدم استخدام أدوات ومعدات الحماية الشخصية أو عدم الالتزام بتطبيق إجراءات السلامة والصحة المهنية عند القيام بأعمال خطرة."
                # 135 (Check 135 before 134 to avoid prefix overlap on "إ تزش")
                elif "ت أأرسأمد" in c or "إ تزشدددد" in c or "اللوحات" in c:
                    c = "إزالة أو تغيير أماكن اللوحات الإرشادية أو التحذيرية الخاصة بالسلامة والصحة المهنية."
                # 134
                elif "إ تزش" in c or "تشسدالم" in c or "تشدمدرتد" in c or "تشسددالم" in c or "تشدمن" in c or "تشصدا" in c:
                    c = "إيقاف أو تعطيل أجهزة السلامة والصحة المهنية (مثل أجهزة الاستشعار، أو كاشفات الدخان، أو كابلات التأريض... الخ)."
                # 136
                elif "أيددد" in c or "حدددذت" in c or "الوقاية المحددة" in c or "متطلبات السلامة" in c:
                    c = "عدم الالتزام بأي من متطلبات السلامة (خوذة السلامة، حذاء السلامة، النظارات الواقية، الكمامات، القفازات، حزام الأمان... الخ) وغيرها من مستلزمات الوقاية المحددة من قبل الأخصائيين في السلامة والصحة المهنية."
                # 137
                elif "تشق اسبأعم" in c or "تصددد" in c:
                    c = "القيام بأعمال في أماكن تتطلب تصريح عمل قبل البدء من المتخصصين في السلامة والصحة المهنية دون الحصول على ترخيص بذلك."
                # 138
                elif "خدم سخد" in c or "رافعة" in c or "عملسمالستشرف" in c:
                    c = "قيادة أو استخدام معدات رافعة أو غيرها من قبل الموظفين غير المرخص لهم بذلك."
                # 139
                elif "ع استشا" in c or "مع ت ستشسالم" in c or "معت ستشسالم" in c:
                    c = "عدم الحفاظ على معدات السلامة والصحة المهنية."
                # 140
                elif "تعسرضست" in c or "الترتيبات" in c or "إهم لست" in c or "تعسرضستآلخرين" in c:
                    c = "تعريض الآخرين للخطر نتيجة إهمال الترتيبات أو التحذيرات أو إجراءات السلامة والصحة المهنية الصادرة من القائمين عليها أو من المنفذين للعمل."
                # 141
                elif "إدخال" in c or "إ ددددددال" in c or "إ دددددددددددددال" in c or "تآلال ستشو سيوط" in c:
                    c = "إدخال أو تشغيل الآلات التي يتطلب تشغيلها إذن مسبق من الإدارة المختصة."
                # 142
                elif "تشع ددب" in c or "الإطفاء" in c or "الإنذار" in c or "تشع دبسبمعدد" in c:
                    c = "اللعب بمعدات إطفاء الحريق أو أجهزة الإنذار المبكر."
                # 143
                elif "طريق سمع" in c or "معاكسة" in c or "مةستشمرلب" in c:
                    c = "قيادة المركبات بطريقة معاكسة داخل شبكة طرقات الشركة."
                # 144
                elif "تج زست" in c or "تجاوز" in c or "تج زستشسرع" in c:
                    c = "تجاوز السرعة المقررة داخل الشركة."
                # 145
                elif "اسإغالم" in c or "الطاقة" in c or "تأددرتددرسأ" in c or "اسإغالمسم" in c:
                    c = "عدم إغلاق مصادر الطاقة الكهربائية أو إغلاق أجهزة التحكم عند الانتهاء من العمل."
                # 146
                elif "تمديدات" in c or "سل رب" in c or "عملستم ي ت" in c:
                    c = "عمل تمديدات كهربائية مؤقتة دون اتباع شروط السلامة والصحة المهنية."
                # 147
                elif "ع اس فع" in c or "حادث عمل" in c:
                    c = "عدم الإبلاغ عن حادث عمل فور وقوعه."
                # 148
                elif "معرقد" in c or "عوائق" in c or "ضددعسمعرقد" in c:
                    c = "وضع عوائق في الطرق المؤدية إلى معدات السلامة والصحة المهنية أو مخارج الطوارئ."
                # 149
                elif "إ دددددددددددددددددد بدددد" in c or "إصابة عمل" in c or "خالل)24(" in c:
                    c = "عدم الإبلاغ عن حدوث إصابة عمل خلال (24) ساعة من وقوع الحادث."
                # 150
                elif "تعم سست" in c or "تلف" in c or "عطل" in c or "سخ خسدد" in c or "تعم سستشوس" in c:
                    c = "التعمد أو التسبب في عطل أو تلف أو خسارة مادية لأي من أجهزة السلامة والصحة المهنية."
                # 151
                elif "وفاة" in c or "التسبب في وفاة" in c or "وفاة أو إصابة" in c or "بسبرف" in c or "منوسدددددد" in c:
                    c = "التسبب في وفاة أو إصابة خطيرة لأحد موظفي الشركة أو غيرهم نتيجة مخالفة قواعد السلامة والصحة المهنية."
                # 152
                elif "إش سأت" in c or "إحداث" in c or "إتلاف" in c:
                    c = "إحداث أضرار أو إتلاف للآلات والمعدات."
                # 153 & 154
                elif "أنرتع" in c or "شرف" in c or "بإض تر" in c or "بأض تر" in c or "تشدد" in c or "شرفد" in c:
                    if "معسس" in c or "مع" in c or "جسيمة" in c or "تسم" in c:
                        c = "التهديد بالاعتداء بالآلات والمعدات (كالمطارق وغيرها من الأدوات الحادة) مع التسبب بأضرار مادية أو إصابات جسدية (جسيمة)."
                    else:
                        c = "التهديد بالاعتداء بالآلات والمعدات (كالمطارق وغيرها من الأدوات الحادة) دون التسبب بأضرار مادية أو إصابات جسدية."
                # Ingestion system triggers
                elif "تاملستك ش فست" in c or "الناتج عن اللعب" in c or "تاملستك ش فست ال ستشن تجسعنستشع بسإنس ت" in c:
                    c = "تحمل تكلفة الكشف والاتصال الناتج عن اللعب بإنذار الحريق"
                
                # Apply standard column and general translations
                for gk, gv in SAFETY_POLICY_GARBLED_MAP.items():
                    if gk in c:
                        c = c.replace(gk, gv)
                        
                cleaned_cells.append(c)
            new_lines.append('|'.join(cleaned_cells))
        else:
            new_lines.append(line)
            
    text = '\n'.join(new_lines)
    
    # Clean other single character artifacts in the table lines
    text = re.sub(r'(\s+)س(\s+)', r'\1 \2', text)
    # remove duplicate spaces
    text = re.sub(r' +', ' ', text)
    return text

def convert_eastern_to_western_numerals(text: str) -> str:
    """
    Converts Eastern Arabic numerals (٠, ١, ٢, ٣, ٤, ٥, ٦, ٧, ٨, ٩)
    to standard Western Arabic/English numerals (0, 1, 2, 3, 4, 5, 6, 7, 8, 9).
    """
    eastern_to_western = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    for east, west in eastern_to_western.items():
        text = text.replace(east, west)
    return text

def insert_spaces_around_numbers(text: str) -> str:
    """
    Inserts a separating space between numerals and Arabic letters (or percent signs)
    if they are adjacent without spaces, preventing OCR text formatting glitches.
    """
    # 1. Western number attached to Arabic character -> add space (e.g. 15يوم -> 15 يوم)
    text = re.sub(r'(\d)([\u0600-\u06FF])', r'\1 \2', text)
    # 2. Arabic character attached to Western number -> add space (e.g. يوم15 -> يوم 15)
    text = re.sub(r'([\u0600-\u06FF])(\d)', r'\1 \2', text)
    # 3. Eastern number attached to Arabic character -> add space
    text = re.sub(r'([\u0660-\u0669])([\u0600-\u06FF])', r'\1 \2', text)
    # 4. Arabic character attached to Eastern number -> add space
    text = re.sub(r'([\u0600-\u06FF])([\u0660-\u0669])', r'\1 \2', text)
    # 5. Percent sign attached to Arabic character (e.g. بنسبة%50 -> بنسبة %50)
    text = re.sub(r'([\u0600-\u06FF])(%)', r'\1 \2', text)
    text = re.sub(r'(%)([\u0600-\u06FF])', r'\1 \2', text)
    return text

def clean_arabic_text(text: str, is_safety_policy: bool = False) -> str:
    if is_safety_policy:
        text = clean_safety_policy_garbled(text)
        
    # Convert Eastern Arabic numerals to standard Western numerals
    text = convert_eastern_to_western_numerals(text)

    # Insert spaces between numbers and Arabic characters
    text = insert_spaces_around_numbers(text)
        
    # Remove OCR specific system notations if present
    text = text.replace("[تم العثور على جدول في هذه الصفحة]:", "")
    text = text.replace("[الترجمة]:", "")
    text = text.replace("[النصوص المصاحبة]:", "")
    
    # 1. Standardize Arabic prefixes (األ -> الأ, اإل -> الإ, اآل -> الآ, اأ -> الأ)
    text = text.replace("األ", "الأ")
    text = text.replace("اإل", "الإ")
    text = text.replace("اآل", "الآ")
    text = text.replace("اأ", "الأ")
    
    # 2. Clean spaces before final letters in words (e.g. خليف ة -> خليفة)
    text = re.sub(
        r'\b([\u0621-\u064A]{2,})\s+([\u0629\u062A\u0645\u0642\u0636\u064A\u0643\u062C\u062E\u062D\u0639\u063A\u0641\u0628\u0644\u0646\u0647\u0623\u0621])\b',
        r'\1\2',
        text
    )
    
    # 3. Fix split prefixes: ال followed by space
    text = re.sub(r'\bال\s+([\u0621-\u064A]+)\b', r'ال\1', text)
    
    # 4. Fix split prefix: و followed by space
    text = re.sub(r'\bو\s+([\u0621-\u064A]+)\b', r'و\1', text)
    
    # 5. Fix hamza mistranslations as '٦' or '6' at end of words
    text = re.sub(r'\b([\u0621-\u064A]+)[\s ]+[٦6]\b', r'\1ء', text)
    text = re.sub(r'([\u0621-\u064A]+)[٦6]\b', r'\1ء', text)
    
    # 6. Specific OCR replacements
    replacements = {
        "الذيتم": "الذي تم",
        "تعدعملية": "تعد عملية",
        "بناءعلى": "بناء على",
        "فينظام": "في نظام",
        "انيكون": "أن يكون",
        "انتدخل": "أن تدخل",
        "وبالتال ي": "وبالتالي",
        "الال تزام": "الالتزام",
        "الال تزا م": "الالتزام",
        "الال تزام ات": "الالتزامات",
        "الال تزا مات": "الالتزامات",
        "الالتزامات": "الالتزامات",
        "اللعين": "المعين",
        "عبد النظا": "عبر النظام",
        "التعريفسات": "التعريفات",
        "التعسيين": "التعيين",
        "انتى": "انتهى",
        "انتم": "أن تم",
        "ان تكون": "أن تكون",
        "ان يتم": "أن يتم",
        "ان تتم": "أن تتم",
        "الا يقل": "ألا يقل",
        "الالعاب": "الألعاب",
        "0.1 الغرفة": "0.1 الغرض",
        "0.1 الغر ض": "0.1 الغرض",
        "liam-E": "E-mail",
        "liamE": "E-mail",
        "liam-e": "E-mail",
        "ygolonhceT": "Technology",
        "skrowteN": "Networks",
        "sresU": "Users",
        "resU": "User",
        "noitamrofnI": "Information",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
        
    return text

def process_file(category: str, filename: str, filepath: Path):
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return
        
    print(f"📄 Processing: {category} / {filename}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    is_safety_policy = "لائحة المخالفات والجزاءات السلامة المهنية" in filename
    
    page_splits = re.split(r'--- (?:بداية الصفحة|جداول الصفحة) \((\d+)\) ---', content)
    
    output_pages = []
    
    if len(page_splits) <= 1:
        clean_text = clean_arabic_text(content.strip(), is_safety_policy)
        output_pages.append(f"<!-- PAGE_START 1 -->\n## صفحة 1\n\n{clean_text}\n<!-- PAGE_END 1 -->")
    else:
        intro_text = page_splits[0].strip()
        if intro_text:
            intro_clean = clean_arabic_text(intro_text, is_safety_policy)
            output_pages.append(intro_clean)
            
        for i in range(1, len(page_splits), 2):
            page_num = page_splits[i]
            page_content = page_splits[i+1].strip()
            
            clean_page_text = clean_arabic_text(page_content, is_safety_policy)
            
            output_pages.append(
                f"<!-- PAGE_START {page_num} -->\n## صفحة {page_num}\n\n{clean_page_text}\n<!-- PAGE_END {page_num} -->"
            )
            
    title_stem = Path(filename).stem
    if title_stem.endswith("_AR"):
        title_stem = title_stem[:-3]
    elif title_stem.endswith("_EN"):
        title_stem = title_stem[:-3]

    doc_title = title_stem.replace("_structured", "").strip()
    doc_title = convert_eastern_to_western_numerals(doc_title)
    doc_title = insert_spaces_around_numbers(doc_title)
    
    markdown_content = f"# {doc_title}\n\n"
    markdown_content += "\n\n".join(output_pages)
    
    dest_dir = OUTPUT_DIR / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    output_filename = f"{doc_title}_structured.md"
    output_filepath = dest_dir / output_filename
    
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    print(f"✅ Saved structured Markdown: {output_filepath}")

def main():
    print(f"🚀 Starting text processing for all 37 target files...")
    for category, filename, filepath in TARGET_FILES:
        process_file(category, filename, filepath)
    print("🎉 All files processed successfully!")

if __name__ == "__main__":
    main()
