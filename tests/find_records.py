from qdrant_client import QdrantClient

def main():
    client = QdrantClient(path="./services/vector_db_service/local_qdrant_db")
    collection_name = "hr_policies"
    
    # Scroll through all records
    offset = None
    count = 0
    found_count = 0
    
    print("Scanning Qdrant database for 'إجازة مخططة' or 'السنوية إلى نوعين'...")
    
    while True:
        records, offset = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        for record in records:
            count += 1
            # fastembed payload document text is stored under "document" key usually, or let's check keys
            payload = record.payload or {}
            # In qdrant client.add(), the document text is stored in the payload
            # Let's print keys of first payload to be sure
            if count == 1:
                print(f"Payload keys: {list(payload.keys())}")
            
            text = payload.get("document", "") or payload.get("text", "") or ""
            
            if "إجازة مخططة" in text or "السنوية إلى نوعين" in text or "مخططة" in text:
                found_count += 1
                print(f"\n--- Found {found_count} ---")
                print(f"ID: {record.id}")
                print(f"Source: {payload.get('source')}, Page: {payload.get('page_number')}")
                print(f"Text content:\n{text}")
                print("-" * 50)
                
        if not offset:
            break
            
    print(f"\nFinished scanning {count} total records. Found {found_count} matching records.")

if __name__ == "__main__":
    main()
