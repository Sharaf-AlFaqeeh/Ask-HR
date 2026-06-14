# services/vector_db_service/data_ingestion.py
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Adjust paths to import core modules and preprocessing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.logger import get_logger
from core.config_manager import get_settings
from core.exceptions import VectorDBError

# تأكد من تحديث هذه الدوال في ملفات cleaner.py و chunker.py بناءً على الكود المحسن السابق
from services.vector_db_service.preprocessing.cleaner import extract_and_clean_pdf
from services.vector_db_service.preprocessing.chunker import chunk_document_pages

logger = get_logger("vector_db_service")
settings = get_settings()

def ingest_documents() -> None:
    """
    Reads local HR policy PDFs, extracts and cleans Arabic text accurately,
    chunks them using LangChain, and ingests into Qdrant with Multilingual Embeddings.
    """
    # 1. Setup paths
    db_service_dir = Path(__file__).parent
    hsa_policies_path = db_service_dir / "HSA_policies"
    qdrant_db_path = Path(settings.vector_db.storage_path)
    
    logger.info("Initializing Data Ingestion Pipeline...")
    
    # 2. Collect files and process chunks
    all_chunks = []
    all_metadata = []
    
    # Process PDF files inside HSA_policies directories
    if hsa_policies_path.exists():
        logger.info(f"Scanning for PDF policies in {hsa_policies_path.absolute()}")
        for pdf_path in hsa_policies_path.rglob("*.pdf"):
            try:
                category = pdf_path.parent.name
                logger.info(f"Processing PDF document: {pdf_path.name} in category: {category}")
                
                # استخدام الدالة المدمجة الجديدة للاستخراج والتنظيف وإصلاح اللغة العربية
                pages_data = extract_and_clean_pdf(pdf_path)
                if not pages_data:
                    logger.warning(f"No text extracted from PDF: {pdf_path.name}")
                    continue
                
                # تقسيم النصوص باستخدام دالة LangChain الجديدة
                # لاحظ أننا نمرر chunk_overlap الآن لضمان التداخل
                chunks = chunk_document_pages(pages_data, chunk_size=600, chunk_overlap=100)
                logger.info(f"Segmented {pdf_path.name} into {len(chunks)} chunks.")
                
                for i, chunk in enumerate(chunks):
                    all_chunks.append(chunk["text"])
                    all_metadata.append({
                        "source": pdf_path.name,
                        "page_number": chunk["page_number"],
                        "category": category,
                        "tenant_id": "HSAGroup",  
                        "chunk_id": i,
                        "language": "ar"
                    })
            except Exception as e:
                logger.error(f"Error processing PDF file {pdf_path.name}", exc_info=True)
    else:
        logger.warning(f"HSA_policies directory not found at {hsa_policies_path.absolute()}")
            
    if not all_chunks:
        logger.warning("No documents found to ingest. Pipeline completed with empty state.")
        return
        
    # 3. Initialize Qdrant Client in local file-based mode
    try:
        from qdrant_client import QdrantClient
        
        logger.info(f"Connecting to local Qdrant DB at path: {qdrant_db_path.absolute()}")
        qdrant_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        client = QdrantClient(path=str(qdrant_db_path))
    except Exception as e:
        logger.error("Failed to initialize Qdrant Client", exc_info=True)
        raise VectorDBError(f"Qdrant DB connection failed: {e}")
        
    # 4. Upsert into Qdrant using fastembed locally
    try:
        collection_name = settings.vector_db.collection_name
        
        # [تعديل هام 1]: إجبار Qdrant على استخدام نموذج متعدد اللغات لفهم العربية
        logger.info("Setting Multilingual Embedding Model...")
        client.set_model("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        
        # [تعديل هام 2]: حذف المجموعة القديمة لتجنب تعارض المتجهات بين النماذج
        if client.collection_exists(collection_name):
            logger.info(f"Deleting existing collection '{collection_name}' to apply new embedding model...")
            client.delete_collection(collection_name=collection_name)
        
        logger.info(f"Re-creating/updating Qdrant collection: '{collection_name}'...")
        client.add(
            collection_name=collection_name,
            documents=all_chunks,
            metadata=all_metadata
        )
        
        logger.info(
            "Ingestion completed successfully!", 
            extra={"collection": collection_name, "total_chunks_indexed": len(all_chunks)}
        )
    except Exception as e:
        logger.error(f"Ingestion failed during Qdrant upsert", exc_info=True)
        raise VectorDBError(f"Qdrant Ingestion Error: {e}")
    finally:
        # [تعديل هام 3]: الإغلاق الآمن في جميع الحالات لمنع أخطاء ويندوز
        logger.info("Closing Qdrant Client connection...")
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    ingest_documents()