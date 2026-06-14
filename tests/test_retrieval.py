# services/vector_db_service/test_retrieval.py

from qdrant_client import QdrantClient

def test_search():
    # 1. الاتصال بقاعدة البيانات
    client = QdrantClient(path="./services/vector_db_service/local_qdrant_db")
    
    # 2. تعيين نفس نموذج التضمين الذي استخدمناه في الإدخال
    client.set_model("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    # 3. السؤال باللغة العربية
    user_query = "ما هي قواعد وإجراءات السفر وبدل المواصلات للموظفين؟"
    print(f"السؤال: {user_query}\n" + "-"*50)
    
    # 4. البحث في قاعدة البيانات (نجلب أقرب 3 نصوص)
    search_results = client.query(
        collection_name="hr_policies",
        query_text=user_query,
        limit=3
    )
    
    # 5. طباعة النتائج
    for i, result in enumerate(search_results, 1):
        print(f"--- النتيجة {i} ---")
        print(f"الملف المصدر: {result.metadata.get('source')}")
        print(f"رقم الصفحة: {result.metadata.get('page_number')}")
        print(f"النص المستخرج:\n{result.document}\n")

if __name__ == "__main__":
    test_search()