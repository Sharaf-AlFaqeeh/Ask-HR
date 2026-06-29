# services/vector_db_service/data_ingestion.py
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Any

# Adjust paths to import core modules and preprocessing modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.logger import get_logger
from core.config_manager import get_settings
from core.exceptions import VectorDBError

# We no longer use extract_and_clean_pdf, we parse the corrected Markdown files
from services.vector_db_service.preprocessing.chunker import chunk_document_pages

logger = get_logger("vector_db_service")
settings = get_settings()

def normalize_name(name: str) -> str:
    # Convert to lowercase
    name = name.lower()
    # Remove extensions and suffixes
    name = re.sub(r'(_structured|_ar|_en|\.md|\.pdf|\.txt)', '', name)
    # Remove spaces
    name = re.sub(r'\s+', '', name)
    # Normalize Arabic letters
    name = name.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    name = name.replace("ة", "ه").replace("ى", "ي")
    name = name.replace("ٔ", "").replace("ٕ", "").replace("ٓ", "") # diacritics
    # Remove punctuation
    name = re.sub(r'[^\w\s]', '', name)
    return name

def ingest_documents() -> None:
    """
    Reads local structured MD policies, parses pages using boundary comments,
    chunks them using LangChain, and ingests into Qdrant with Multilingual Embeddings.
    """
    # 1. Setup paths
    db_service_dir = Path(__file__).parent
    hsa_policies_path = db_service_dir / "HSA_policies"
    structured_md_path = db_service_dir / "structured_texts_md"
    qdrant_db_path = Path(settings.vector_db.storage_path)
    
    logger.info("Initializing Data Ingestion Pipeline from structured Markdown...")
    
    # Map original PDF filenames by normalized names
    pdf_map = {}
    if hsa_policies_path.exists():
        logger.info(f"Mapping PDFs in {hsa_policies_path.absolute()}")
        for pdf_path in hsa_policies_path.rglob("*.pdf"):
            norm_name = normalize_name(pdf_path.name)
            pdf_map[norm_name] = pdf_path.name
    else:
        logger.warning(f"HSA_policies directory not found at {hsa_policies_path.absolute()}")
        
    # 2. Collect files and process chunks
    all_chunks = []
    all_metadata = []
    
    if structured_md_path.exists():
        logger.info(f"Scanning for structured Markdown files in {structured_md_path.absolute()}")
        for md_path in structured_md_path.rglob("*.md"):
            try:
                category = md_path.parent.name
                logger.info(f"Processing structured document: {md_path.name} in category: {category}")
                
                # Read Markdown content
                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Find matching original PDF name
                norm_md = normalize_name(md_path.name)
                original_pdf_name = pdf_map.get(norm_md)
                if not original_pdf_name:
                    original_pdf_name = md_path.name.replace("_structured.md", ".pdf")
                    logger.warning(f"Could not find matching PDF for {md_path.name}, falling back to {original_pdf_name}")
                
                # Parse pages using page boundaries comments
                pages_data = []
                page_matches = re.findall(r'<!-- PAGE_START (\d+) -->\s*(.*?)\s*<!-- PAGE_END \1 -->', content, re.DOTALL)
                
                for match in page_matches:
                    page_num = int(match[0])
                    page_text = match[1].strip()
                    # Strip markdown page title if present (e.g. ## صفحة X)
                    page_text = re.sub(r'^##\s+صفحة\s+\d+\s*\n*', '', page_text).strip()
                    
                    if page_text:
                        pages_data.append({
                            "page_number": page_num,
                            "text": page_text
                        })
                
                if not pages_data:
                    logger.warning(f"No pages extracted from Markdown file: {md_path.name}")
                    continue
                
                # Chunk using LangChain chunker
                chunks = chunk_document_pages(pages_data, chunk_size=600, chunk_overlap=100)
                logger.info(f"Segmented {md_path.name} into {len(chunks)} chunks.")
                
                for i, chunk in enumerate(chunks):
                    all_chunks.append(chunk["text"])
                    all_metadata.append({
                        "source": original_pdf_name,
                        "page_number": chunk["page_number"],
                        "category": category,
                        "tenant_id": "HSAGroup",  
                        "chunk_id": i,
                        "language": "ar"
                    })
            except Exception as e:
                logger.error(f"Error processing MD file {md_path.name}", exc_info=True)
    else:
        logger.error(f"structured_texts_md directory not found at {structured_md_path.absolute()}")
            
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