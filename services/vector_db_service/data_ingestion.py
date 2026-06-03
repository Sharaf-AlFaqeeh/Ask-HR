import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Adjust path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from core.logger import get_logger
from core.config_manager import get_settings
from core.exceptions import VectorDBError

logger = get_logger("vector_db_service")
settings = get_settings()

def create_mock_documents_if_empty(docs_dir: Path) -> None:
    """
    Creates high-quality mock HR policies for HSA Group if raw_documents directory is empty.
    """
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    mock_files = {
        "hsa_leave_policy.txt": (
            "سياسة الإجازات الرسمية والسنوية لمجموعة هائل سعيد أنعم (HSA Group):\n\n"
            "1. الإجازة السنوية المدفوعة الأجر:\n"
            "- يستحق كل موظف إجازة سنوية مدتها 30 يوماً تقويمياً مدفوعة الأجر بالكامل بعد إتمام عام كامل من الخدمة المتواصلة.\n"
            "- يجب التنسيق وتقديم طلب الإجازة قبل 14 يوماً على الأقل من تاريخ بدء الإجازة لضمان استمرارية العمل.\n"
            "- يسمح بترحيل ما لا يزيد عن 10 أيام من الإجازة غير المستخدمة إلى العام التالي بعد موافقة مدير الموارد البشرية.\n\n"
            "2. الإجازة المرضية:\n"
            "- يستحق الموظف إجازة مرضية مدفوعة الأجر بالكامل لمدة تصل إلى 15 يوماً في السنة، بناءً على تقرير طبي معتمد.\n"
            "- إذا تجاوزت الإجازة المرضية 15 يوماً، يتم تخفيض الراتب وفق قانون العمل المعمول به (75% من الراتب للأيام الـ 15 التالية).\n\n"
            "3. إجازة الأبوة والأمومة:\n"
            "- تستحق الموظفة إجازة وضع مدفوعة الأجر بالكامل لمدة 70 يوماً.\n"
            "- يستحق الموظف الأب إجازة أبوة مدفوعة الأجر لمدة 3 أيام عند ولادة طفل له."
        ),
        "hsa_benefits_policy.txt": (
            "سياسة البدلات والتعويضات والمزايا الوظيفية بمجموعة HSA Group:\n\n"
            "1. بدل السكن:\n"
            "- تمنح المجموعة جميع الموظفين من الدرجة الرابعة فما فوق بدل سكن شهري يعادل 25% من الراتب الأساسي، أو توفر سكناً عينياً ملائماً.\n"
            "- يصرف بدل السكن بالتزامن مع الراتب الشهري ويخضع للتقييم السنوي.\n\n"
            "2. التأمين الطبي:\n"
            "- توفر HSA Group تغطية تأمين طبي شاملة (فئة أ/Class A) للموظف وعائلته المباشرة (الزوج/الزوجة والأبناء حتى سن 18 عاماً).\n"
            "- تشمل التغطية الرعاية الطبية في المستشفيات والعيادات الخارجية المعتمدة، مع نسبة مساهمة للموظف لا تتعدى 10% للعيادات الخارجية.\n\n"
            "3. بدل المواصلات:\n"
            "- يصرف بدل مواصلات شهري لجميع الموظفين بحسب فئاتهم الوظيفية لتغطية تكاليف التنقل للعمل:\n"
            "  * الفئة التشغيلية: 150 دولار شهرياً.\n"
            "  * الفئة الإدارية: 300 دولار شهرياً أو سيارة مخصصة من الشركة."
        )
    }
    
    for filename, content in mock_files.items():
        file_path = docs_dir / filename
        if not file_path.exists():
            logger.info(f"Creating mock HR policy: {filename}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """
    Splits text into semantic chunks of roughly chunk_size characters with overlap.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) < chunk_size:
            current_chunk += paragraph + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def ingest_documents() -> None:
    """
    Reads local HR policy files, embeds them, and ingests into Qdrant.
    """
    # 1. Setup paths
    raw_docs_path = Path(settings.vector_db.storage_path).parent / "raw_documents"
    qdrant_db_path = Path(settings.vector_db.storage_path)
    
    logger.info("Initializing Data Ingestion Pipeline...")
    create_mock_documents_if_empty(raw_docs_path)
    
    # 2. Initialize Qdrant Client in local file-based mode
    try:
        from qdrant_client import QdrantClient
        
        logger.info(f"Connecting to local Qdrant DB at path: {qdrant_db_path.absolute()}")
        qdrant_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        client = QdrantClient(path=str(qdrant_db_path))
    except Exception as e:
        logger.error("Failed to initialize Qdrant Client", exc_info=True)
        raise VectorDBError(f"Qdrant DB connection failed: {e}")
        
    # 3. Read raw files
    all_chunks = []
    all_metadata = []
    
    for file_path in raw_docs_path.glob("*.txt"):
        try:
            logger.info(f"Processing document: {file_path.name}")
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
                
            chunks = chunk_text(text)
            logger.info(f"Split {file_path.name} into {len(chunks)} chunks.")
            
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadata.append({
                    "source": file_path.name,
                    "chunk_id": i,
                    "content_preview": chunk[:50] + "..."
                })
        except Exception as e:
            logger.error(f"Error reading file {file_path.name}", exc_info=True)
            
    if not all_chunks:
        logger.warning("No documents found to ingest. Pipeline completed with empty state.")
        return
        
    # 4. Upsert into Qdrant using fastembed locally
    try:
        collection_name = settings.vector_db.collection_name
        logger.info(f"Re-creating/updating Qdrant collection: '{collection_name}'...")
        
        # client.add handles everything: collection creation, model loading (fastembed), embedding, and upserting.
        # It runs entirely locally on CPU and is incredibly efficient!
        client.add(
            collection_name=collection_name,
            documents=all_chunks,
            metadata=all_metadata
        )
        
        logger.info(
            "Ingestion completed successfully!", 
            extra_fields={"collection": collection_name, "total_chunks_indexed": len(all_chunks)}
        )
    except Exception as e:
        logger.error(f"Ingestion failed during Qdrant upsert", exc_info=True)
        raise VectorDBError(f"Qdrant Ingestion Error: {e}")

if __name__ == "__main__":
    ingest_documents()
