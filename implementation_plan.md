# خطة تأسيس مشروع Ask HR Enterprise AI Orchestration Engine

مشروع **Ask HR** هو محرك أوركسترا متكامل للذكاء الاصطناعي (AI Orchestration Engine) مصمم للعمل في بيئة مؤسسية متعددة المستأجرين (Multi-tenant) وقابلة للتوسع بشكل هائل. تم تصميم هذا النظام ليكون خياراً مرناً وقابلاً للتطوير من هيكلية محلية بسيطة إلى نظام Microservices موزع بالكامل، مع الاستعداد للتكامل مع أنظمة SAP SuccessFactors وأنظمة مراكز الاتصال (Call Center).

---

## مراجعة المستخدم المطلوبة (User Review Required)

> [!IMPORTANT]
> 1. **الاعتماد المحلي (Local-First):** سيتم تشغيل البنية التحتية بالكامل محلياً (Local CPU/GPU) دون الحاجة لخوادم سحابية أو Docker في هذه المرحلة، مع توفير كافة ملفات الـ Dockerfile و docker-compose لضمان جاهزية النشر المستقبلي.
> 2. **نموذج Qwen المحلي:** لن نقوم بتحميل أي نماذج من الإنترنت. سنقوم بإعداد النظام للاتصال بنموذج Qwen المحلي الخاص بك واستدعائه محلياً بالكامل ومباشرةً من داخل المشروع عبر مكتبة `llama-cpp-python` التي سنقوم بتشغيلها كخدمة مستقلة داخل المشروع (`services/llm_inference_service`) لتوفير خادم محلي متوافق مع OpenAI API. سنشرح لك في ملف `README.md` كيفية وضع ملف النموذج وتحديث مساره في ملف الإعدادات `config.yaml`.
> 3. **قاعدة بيانات المتجهات المحلية (Vector DB):** سنستخدم مكتبة `Qdrant` المحلية التي تخزن البيانات مباشرة في مجلد محلي (`path="local_qdrant_db"`) لتبسيط التطوير وتجنب تشغيل خوادم منفصلة.

---

## أسئلة مفتوحة للمناقشة (Open Questions)

> [!NOTE]
> يرجى مراجعة هذه النقاط وإبداء رأيك بها إذا كنت تفضل تعديلاً معيناً، وسنقوم باعتمادها مباشرة في التنفيذ:
> 1. **منفذ تشغيل LLM Inference Server:** سنقوم بضبط المنفذ الافتراضي لخادم نموذج Qwen المحلي على `8000` (أو أي منفذ تفضله). هل ترغب في استخدام منفذ مخصص؟
> 2. **استخراج الكيانات (Entity Extraction):** للتكامل المستقبلي مع SAP، هل تفضل أن نعتمد على استخراج الكيانات باستخدام التعبيرات المنتظمة (Regex/Rule-based) أم من خلال توجيه طلبات للـ LLM (LLM-based Entity Extraction) لاستخلاصها من النص مباشرة؟ (سنقوم بدمج الطريقتين كـ Hybrid لضمان أعلى دقة).

---

## التغييرات المقترحة والهيكل التنظيمي (Proposed Changes)

سنقوم ببناء هيكلية المجلدات التالية وتجهيز كافة الملفات البرمجية بالكامل وبأعلى معايير الجودة (تتضمن معالجة الأخطاء الشاملة، التحقق من البيانات باستخدام Pydantic، والتسجيل المهيكل للمعلومات Structured Logging).

```text
AskHR_Enterprise/
├── .env.example
├── config.yaml                    # إعدادات مسار النموذج، قاعدة البيانات، والمنافذ
├── docker-compose.yml             # جاهز للنشر المستقبلي (Scaffolding)
├── requirements.txt               # كافة المكتبات المطلوبة للمشروع
├── README.md                      # دليل التشغيل والتهيئة خطوة بخطوة
│
├── core/                          # المكونات المشتركة للمؤسسة
│   ├── __init__.py
│   ├── logger.py                  # نظام التسجيل المهيكل (Structured JSON Logging)
│   ├── config_manager.py          # التحقق من الإعدادات عبر Pydantic BaseSettings
│   └── exceptions.py              # معالجة الأخطاء المخصصة للمؤسسة
│
├── services/
│   ├── __init__.py
│   ├── llm_inference_service/     # خدمة تشغيل واستدعاء نموذج Qwen المحلي
│   │   ├── Dockerfile
│   │   ├── server.py              # خادم FastAPI محلي متوافق مع OpenAI API
│   │   └── models/                # مجلد فارغ لوضع نموذج Qwen فيه
│   │
│   ├── vector_db_service/         # خدمة الـ RAG والتعامل مع قاعدة المتجهات Qdrant
│   │   ├── Dockerfile
│   │   ├── data_ingestion.py      # تفكيك وتجهيز ملفات السياسات وحفظ متجهاتها
│   │   ├── raw_documents/         # مجلد لوضع ملفات سياسات الموارد البشرية (txt/pdf)
│   │   └── local_qdrant_db/       # مجلد حفظ بيانات Qdrant المحلية
│   │
│   └── orchestrator_service/      # الخدمة الرئيسية وتوجيه الطلبات
│       ├── Dockerfile
│       ├── main.py                # نقطة انطلاق تطبيق FastAPI والمسارات الرئيسية
│       ├── api/
│       │   ├── __init__.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       └── chat.py        # واجهة استقبال طلبات المحادثة
│       ├── nlp/
│       │   ├── __init__.py
│       │   ├── intent_router.py   # توجيه الطلبات (RAG vs SAP Action)
│       │   └── entity_extractor.py # استخراج البيانات (ID, Leave Type, Dates)
│       ├── rag/
│       │   ├── __init__.py
│       │   └── retriever.py       # استرجاع سياق السياسات وصياغة طلب الـ LLM
│       └── sap_integration/
│           ├── __init__.py
│           └── client.py          # محاكاة الاتصال بنظام SAP SuccessFactors
```

---

### تفاصيل المكونات (Component Design)

#### 1. المكونات المشتركة (Core Layer)
*   **[NEW] [logger.py](file:///p:/____AI____/HSAGroup/AskHRPro/core/logger.py):** تأسيس نظام تسجيل أحداث مهيكل (Structured Logging) يخرج السجلات بصيغة JSON لسهولة مراقبتها وتحليلها مستقبلاً عبر أدوات مثل ELK أو Datadog، مع دعم إضافة Trace IDs لربط الطلبات.
*   **[NEW] [config_manager.py](file:///p:/____AI____/HSAGroup/AskHRPro/core/config_manager.py):** إدارة وتحقق من صحة ملفات الإعدادات (`config.yaml` و `.env`) باستخدام Pydantic لضمان عدم تشغيل النظام بأي قيم خاطئة أو ناقصة.
*   **[NEW] [exceptions.py](file:///p:/____AI____/HSAGroup/AskHRPro/core/exceptions.py):** هيكل موحد لمعالجة واسترجاع أخطاء المؤسسة (Enterprise Exception Handler) يدعم ترجمة الأخطاء البرمجية إلى رسائل آمنة للمستخدم النهائي مع الاحتفاظ بالتفاصيل الدقيقة للمطورين في السجلات.

#### 2. خدمة تشغيل النموذج المحلي (LLM Inference Service)
*   **[NEW] [server.py](file:///p:/____AI____/HSAGroup/AskHRPro/services/llm_inference_service/server.py):** توفير خادم ويب محلي يعمل كـ wrapper لـ `llama-cpp-python` يعرض واجهة توافقية بنسبة 100% مع OpenAI Chat Completions API. هذا يسمح بالتبديل مستقبلاً لأي خادم آخر بسهولة مطلقة.
*   **[NEW] [Dockerfile](file:///p:/____AI____/HSAGroup/AskHRPro/services/llm_inference_service/Dockerfile):** ملف بناء حاوية الـ Docker مع تجهيز متطلبات تشغيل النماذج محلياً.

#### 3. خدمة قاعدة بيانات المتجهات RAG (Vector DB & Ingestion Service)
*   **[NEW] [data_ingestion.py](file:///p:/____AI____/HSAGroup/AskHRPro/services/vector_db_service/data_ingestion.py):** سكربت ذكي يقوم بقراءة الملفات النصية لسياسات الموارد البشرية من مجلد `raw_documents` وتقطيعها (Chunking) ثم تحويلها لمتجهات وحفظها محلياً في قاعدة `Qdrant` باستخدام تضمين محلي فائق السرعة.
*   **[NEW] [raw_documents/](file:///p:/____AI____/HSAGroup/AskHRPro/services/vector_db_service/raw_documents/):** سننشئ مستندات تجريبية لسياسات الموارد البشرية (مثل سياسة الإجازات، وسياسة البدلات) لاختبار كفاءة الـ RAG.

#### 4. خدمة الأوركسترا الرئيسية (Orchestrator Service)
*   **[NEW] [main.py](file:///p:/____AI____/HSAGroup/AskHRPro/services/orchestrator_service/main.py):** خادم FastAPI الأساسي الذي يربط الخدمات معاً، يدير الـ Middleware (تتبع الطلبات، منع هجمات الاختراق، معالجة الـ CORS)، ويحتوي على معالج الأخطاء العالمي.
*   **[NEW] [chat.py](file:///p:/____AI____/HSAGroup/AskHRPro/services/orchestrator_service/api/v1/chat.py):** استقبال رسائل الموظف وتوجيهها للمحرك الذكي.
*   **[NEW] [intent_router.py](file:///p:/____AI____/HSAGroup/AskHRPro/services/orchestrator_service/nlp/intent_router.py):** محرك تصنيف ذكي يحلل مدخلات الموظف لتحديد هل المطلوب استفسار عن السياسات (RAG) أم رغبة في تنفيذ إجراء مثل تقديم إجازة أو طلب كشف راتب (SAP Action).
*   **[NEW] [entity_extractor.py](file:///p:/____AI____/HSAGroup/AskHRPro/services/orchestrator_service/nlp/entity_extractor.py):** مستخرج الكيانات الذكي لاستخلاص البيانات الأساسية المطلوبة لإجراءات SAP (مثل استخراج الرقم الوظيفي Employee ID، نوع الإجازة Leave Type، والتواريخ).
*   **[NEW] [retriever.py](file:///p:/____AI____/HSAGroup/AskHRPro/services/orchestrator_service/rag/retriever.py):** استرجاع المستندات ذات الصلة من Qdrant وبناء قالب الـ Prompt الموجه للـ LLM لضمان إجابة دقيقة خالية من الهلوسة الذكائية.
*   **[NEW] [client.py](file:///p:/____AI____/HSAGroup/AskHRPro/services/orchestrator_service/sap_integration/client.py):** وحدة محاكاة متكاملة للتكامل مع SAP SuccessFactors تقوم بعرض شكل البيانات المتدفقة مستقبلاً وتسجل الأحداث التي كان سيتلقاها الـ API الحقيقي.

---

## خطة التحقق والاختبار (Verification Plan)

لتأكيد عمل النظام بأعلى جودة وخلوه تماماً من الأخطاء:

### الاختبارات البرمجية الذاتية (Automated Tests)
1. **اختبار هيكلية الإعدادات:** تشغيل سكربت التحقق من صحة ملفات الإعدادات والـ Environment variables.
2. **اختبار فحص معالجة الكيانات وتصنيف النوايا:** وحدة اختبار مستقلة لتصنيف عينات من نصوص المستخدمين (مثال: "أريد تقديم إجازة مرضية" -> تصنيف النية كـ SAP وتحديد الكيان كـ "إجازة مرضية").
3. **اختبار الـ RAG محلياً:** التحقق من إدراج واسترجاع البيانات من قاعدة بيانات Qdrant المحلية للتأكد من ربط المتجهات بشكل سليم.

### التحقق اليدوي (Manual Verification)
1. **تشغيل خادم FastAPI:** سنقوم بتشغيل خادم الأوركسترا محلياً ونستعرض واجهة الـ API التفاعلية (FastAPI Swagger UI) لتجربة المسارات مباشرة.
2. **فحص الـ Logs المهيكلة:** التأكد من طباعة السجلات بصيغة JSON متناسقة واحتوائها على كافة بيانات التتبع.
