import os
import sys
from pathlib import Path
from qdrant_client import QdrantClient

# Adjust paths to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.config_manager import get_settings

settings = get_settings()
qdrant_db_path = Path(settings.vector_db.storage_path)
collection_name = settings.vector_db.collection_name

print(f"Connecting to Qdrant at: {qdrant_db_path.absolute()}")
if not qdrant_db_path.exists():
    print("❌ Qdrant database directory does not exist.")
    sys.exit(1)

try:
    client = QdrantClient(path=str(qdrant_db_path))
    collections = client.get_collections()
    print("Collections found:")
    for col in collections.collections:
        print(f" - {col.name}")
        info = client.get_collection(col.name)
        print(f"   Points count: {info.points_count}")
        print(f"   Status: {info.status}")
        
    if collection_name in [c.name for c in collections.collections]:
        print(f"\nFetching top 5 points from '{collection_name}':")
        # Scroll some points
        points, next_page = client.scroll(
            collection_name=collection_name,
            limit=5,
            with_payload=True,
            with_vectors=False
        )
        for p in points:
            print(f" - Point ID: {p.id}")
            print(f"   Metadata: {p.payload.get('metadata') if p.payload else None}")
            doc = p.payload.get('document') if p.payload else None
            if doc:
                snippet = doc[:100].replace('\n', ' ')
                print(f"   Document snippet: {snippet}...")
    else:
        print(f"❌ Collection '{collection_name}' not found in Qdrant database.")

    client.close()
except Exception as e:
    print(f"❌ Error querying Qdrant: {e}")
