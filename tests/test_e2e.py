import asyncio
import sys
import os

# ضبط المسارات للوصول إلى المجلدات الجذرية
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.orchestrator_service.infrastructure.llm_clients.openai_client import OpenAICompatibleLLMClient
from services.orchestrator_service.rag.retriever import RAGRetriever
from services.orchestrator_service.application.prompt_registry import PromptRegistry

async def test_rag_llm_integration():
    print("🚀 بدء اختبار التكامل بين قاعدة البيانات المتجهة ونموذج اللغة...")
    
    # 1. تهيئة المكونات
    retriever = RAGRetriever()
    llm_client = OpenAICompatibleLLMClient()

    query = "ما هي قواعد وإجراءات السفر وبدل المواصلات للموظفين؟"
    print(f"\n👤 السؤال: {query}\n" + "-"*50)

    # 2. جلب السياق من Qdrant
    print("🔍 جاري البحث في قاعدة البيانات (Qdrant)...")
    context = retriever.retrieve_context(query)
    
    if not context:
        print("❌ لم يتم العثور على سياق. تأكد من نجاح عملية الرفع (Ingestion).")
        return
        
    print(f"✅ تم جلب السياق بنجاح. (طول النص المستخرج: {len(context)} حرف)\n" + "-"*50)

    # 3. صياغة الـ Prompt
    system_instructions = PromptRegistry.RAG_SYSTEM_TEMPLATE.format(context=context)
    messages = [
        {"role": "system", "content": system_instructions},
        {"role": "user", "content": query}
    ]

    # 4. إرسال الطلب إلى السيرفر المحلي
    print("🤖 جاري إرسال السياق والسؤال إلى سيرفر LLM...")
    response = await llm_client.query_llm(messages)

    print("\n" + "="*50)
    print("✨ إجابة النظام النهائية (AskHR):")
    print("="*50)
    print(response)
    print("="*50)

if __name__ == "__main__":
    # تشغيل الدالة غير المتزامنة
    asyncio.run(test_rag_llm_integration())