from qdrant_client import QdrantClient

# 1. الاتصال بقاعدة البيانات المحلية بناءً على مسار المجلد لديك
client = QdrantClient(path="./services/vector_db_service/local_qdrant_db")

collection_name = "hr_policies"

# 2. التحقق من حالة المجموعة (عدد السجلات، وما إلى ذلك)
collection_info = client.get_collection(collection_name=collection_name)
print(f"Collection Info: {collection_info}")

# 3. استرجاع بعض السجلات (Points) للتحقق من المحتوى النصي
# نستخدم scroll لجلب عدد معين من السجلات (مثلاً 3 سجلات)
records, _ = client.scroll(
    collection_name=collection_name,
    limit=3,
    with_payload=True, # لإظهار النصوص (البيانات الوصفية) المرفقة
    with_vectors=False # يمكنك جعلها True إذا أردت رؤية الأرقام الموجهة
)

print("\n--- Sample Records ---")
for record in records:
    print(f"ID: {record.id}")
    print(f"Payload (Text): {record.payload}")
    print("-" * 20)