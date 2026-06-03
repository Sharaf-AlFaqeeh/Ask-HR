import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Adjust path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from core.logger import get_logger
from core.config_manager import get_settings
from core.exceptions import VectorDBError

logger = get_logger("rag_retriever")
settings = get_settings()

class RAGRetriever:
    """
    Connects to local Qdrant collection to retrieve contextually relevant HR policies
    for user queries, enabling zero-shot grounded answers.
    """
    def __init__(self):
        self.collection_name = settings.vector_db.collection_name
        self.qdrant_path = Path(settings.vector_db.storage_path)
        self.client = None
        self.init_qdrant_client()

    def init_qdrant_client(self) -> None:
        """
        Initializes connection to file-based Qdrant.
        """
        if not self.qdrant_path.exists():
            logger.warning(
                f"Qdrant storage directory does not exist yet at {self.qdrant_path.absolute()}. "
                "Retrievals will return empty until data ingestion runs."
            )
            return

        try:
            from qdrant_client import QdrantClient
            logger.info(f"Connecting RAG Retriever to Qdrant at: {self.qdrant_path.absolute()}")
            self.client = QdrantClient(path=str(self.qdrant_path))
        except Exception as e:
            logger.error("Failed to connect to local Qdrant DB", exc_info=True)
            self.client = None

    def retrieve_context(self, query: str, limit: int = 3) -> str:
        """
        Queries Qdrant to retrieve relevant text chunks.
        """
        if not self.client:
            logger.warning("Qdrant Client is not initialized. Returning empty context.")
            return ""

        try:
            # Check if collection exists
            collections_info = self.client.get_collections()
            collection_names = [col.name for col in collections_info.collections]
            
            if self.collection_name not in collection_names:
                logger.warning(
                    f"Collection '{self.collection_name}' not found. "
                    "Please run the ingestion script 'data_ingestion.py' to populate data."
                )
                return ""

            logger.info(f"Searching Qdrant collection '{self.collection_name}' for query...")
            
            # Perform query. client.query uses local fastembed model automatically
            results = self.client.query(
                collection_name=self.collection_name,
                query_text=query,
                limit=limit
            )
            
            if not results:
                logger.info("No matching contexts found in Qdrant.")
                return ""
                
            logger.info(f"Retrieved {len(results)} relevant chunks from Qdrant.")
            
            # Join chunks
            context_blocks = []
            for i, res in enumerate(results):
                # Retrieve document text from chunk
                doc_text = res.document
                source = res.metadata.get("source", "Unknown Policy")
                context_blocks.append(f"[مصدر: {source}]\n{doc_text}")
                
            return "\n\n---\n\n".join(context_blocks)
            
        except Exception as e:
            logger.error("Error retrieving context from Qdrant", exc_info=True)
            # Fail silently to avoid breaking the chat session (return empty context)
            return ""

    def build_rag_prompt(self, query: str, context: str) -> List[Dict[str, str]]:
        """
        Builds a robust grounded system prompt instructing Qwen to strictly use
        the retrieved context for HR queries, mitigating AI hallucination.
        """
        system_instructions = (
            "أنت خبير محترف ومستشار الموارد البشرية لمجموعة هائل سعيد أنعم (HSA Group).\n"
            "مهمتك هي الإجابة بدقة وأمانة على استفسارات الموظف باستخدام السياق المسترجع المرفق فقط.\n"
            "اتبع القواعد التالية بدقة:\n"
            "1. إذا لم تجد الإجابة في السياق المرفق، قل بوضوح ولطف: 'عذراً، لم أجد إجابة دقيقة لهذا الاستفسار في لوائح سياسات الموارد البشرية الحالية، يرجى التواصل مع إدارة الموارد البشرية مباشرة.'\n"
            "2. لا تقم أبداً باختلاق أو تخمين أي سياسات أو تواريخ أو أرقام غير موجودة في السياق المرفق.\n"
            "3. أجب بلغة مهنية وودودة للغاية باللغة العربية الفصحى.\n\n"
            "السياق المسترجع من اللوائح والسياسات الرسمية لمجموعة HSA:\n"
            "=========================================\n"
            f"{context}\n"
            "=========================================\n"
        )
        
        return [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": query}
        ]
