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
from services.vector_db_service.preprocessing.cleaner import extract_text_from_pdf, clean_arabic_text
from services.vector_db_service.preprocessing.chunker import chunk_document_pages

logger = get_logger("vector_db_service")
settings = get_settings()

def ingest_documents() -> None:
    """
    Reads local HR policy PDFs and text files, cleans/chunks them, and ingests into Qdrant.
    """
    # 1. Setup paths
    db_service_dir = Path(__file__).parent
    hsa_policies_path = db_service_dir / "HSA_policies"
    # raw_docs_path = db_service_dir / "raw_documents"
    qdrant_db_path = Path(settings.vector_db.storage_path)
    
    logger.info("Initializing Data Ingestion Pipeline...")
    
    # 2. Collect files and process chunks
    all_chunks = []
    all_metadata = []
    
    # Process PDF files inside HSA_policies directories (Real System Data)
    if hsa_policies_path.exists():
        logger.info(f"Scanning for PDF policies in {hsa_policies_path.absolute()}")
        for pdf_path in hsa_policies_path.rglob("*.pdf"):
            try:
                category = pdf_path.parent.name
                logger.info(f"Processing PDF document: {pdf_path.name} in category: {category}")
                
                # Extract page data
                pages_data = extract_text_from_pdf(pdf_path)
                if not pages_data:
                    logger.warning(f"No text extracted from PDF: {pdf_path.name}")
                    continue
                
                # Clean text for each page
                cleaned_pages = []
                for p in pages_data:
                    cleaned_text = clean_arabic_text(p["text"])
                    if cleaned_text:
                        cleaned_pages.append({
                            "page_number": p["page_number"],
                            "text": cleaned_text
                        })
                
                # Segment pages into chunks
                chunks = chunk_document_pages(cleaned_pages, chunk_size=600, overlap=100)
                logger.info(f"Segmented {pdf_path.name} into {len(chunks)} chunks.")
                
                for i, chunk in enumerate(chunks):
                    all_chunks.append(chunk["text"])
                    all_metadata.append({
                        "source": pdf_path.name,
                        "page_number": chunk["page_number"],
                        "category": category,
                        "tenant_id": "HSA_Group",  # Set default Tenant ID for group policies
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
        logger.info(f"Re-creating/updating Qdrant collection: '{collection_name}'...")
        
        # client.add handles everything: collection creation, model loading, embedding, and upserting.
        # It runs entirely locally on CPU and is incredibly efficient!
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

if __name__ == "__main__":
    ingest_documents()
