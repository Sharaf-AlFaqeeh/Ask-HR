# tests/verify_qdrant_data.py
import os
import sys
from pathlib import Path

# Adjust path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.config_manager import get_settings

def verify_qdrant():
    settings = get_settings()
    collection_name = settings.vector_db.collection_name
    qdrant_path = Path(settings.vector_db.storage_path)

    print(f"=== Qdrant Collection Verification ===")
    print(f"Database Path: {qdrant_path.absolute()}")
    print(f"Collection Name: {collection_name}")
    print("======================================\n")

    if not qdrant_path.exists():
        print("Error: Qdrant local storage path does not exist!")
        sys.exit(1)

    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(path=str(qdrant_path))
        
        # 1. Get collection information
        collection_info = client.get_collection(collection_name=collection_name)
        print("Collection Status: ACTIVE")
        print(f"Indexed Vectors Count (approx): {collection_info.points_count}")
        print(f"Optimized status: {collection_info.status}")
        print("--------------------------------------\n")

        # 2. Query test
        test_queries = [
            "ما هي شروط الإجازة السنوية؟",
            "ما هو بدل السكن للموظفين؟",
            "ما هي سياسة استخدام البريد الإلكتروني؟"
        ]

        for query in test_queries:
            print(f"Query: '{query}'")
            results = client.query(
                collection_name=collection_name,
                query_text=query,
                limit=2
            )
            
            if not results:
                print("  -> No results returned.")
            else:
                for idx, res in enumerate(results):
                    source = res.metadata.get("source", "N/A")
                    page = res.metadata.get("page_number", "N/A")
                    category = res.metadata.get("category", "N/A")
                    tenant = res.metadata.get("tenant_id", "N/A")
                    print(f"  [{idx + 1}] Source: {source} (Page: {page}) | Category: {category} | Tenant: {tenant}")
                    print(f"      Snippet: {res.document[:150]}...")
            print("--------------------------------------\n")

    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_qdrant()
