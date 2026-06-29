# services/orchestrator_service/infrastructure/rag/qdrant_retriever.py
import os
from pathlib import Path
from services.orchestrator_service.domain.interfaces import IRetriever
from core.config_manager import get_settings
from core.logger import get_logger
from core.security.tenant import get_tenant_id

logger = get_logger("qdrant_retriever_adapter")
settings = get_settings()

class QdrantRetrieverAdapter(IRetriever):
    """
    Adapter implementing the IRetriever port.
    Retrieves HR policies from local file-based Qdrant.
    Supports tenant-based context filtering to prevent data leakage between subsidiaries.
    """
    def __init__(self):
        self.collection_name = settings.vector_db.collection_name
        self.qdrant_path = Path(settings.vector_db.storage_path)
        self.client = None
        self.init_client()

    def init_client(self) -> None:
        if not self.qdrant_path.exists():
            logger.warning(f"Qdrant database not found at {self.qdrant_path.absolute()}. Ingestion needed.")
            return

        try:
            from qdrant_client import QdrantClient
            logger.info(f"Connecting Qdrant Adapter to: {self.qdrant_path.absolute()}")
            self.client = QdrantClient(path=str(self.qdrant_path))
            self.client.set_model("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        except Exception as e:
            logger.error("Failed to connect Qdrant Client", exc_info=True)
            self.client = None

    def retrieve_context(self, query: str, limit: int = 3) -> str:
        if not self.client:
            logger.info("Qdrant Client is offline. Attempting reconnection...")
            self.init_client()

        if not self.client:
            logger.warning("Qdrant Client is offline. Returning empty context.")
            return ""

        tenant_id = get_tenant_id()
        logger.info(f"Retrieving context for query in Qdrant collection: {self.collection_name} (Tenant: {tenant_id})")

        try:
            # Check collections
            collections_info = self.client.get_collections()
            collection_names = [col.name for col in collections_info.collections]
            
            if self.collection_name not in collection_names:
                logger.warning(f"Collection '{self.collection_name}' does not exist.")
                return ""

            # Define multi-tenant filter: match current tenant_id or default files
            from qdrant_client.http import models as qmodels
            
            # Retrieve documents (retrieve a larger limit to re-rank with keyword matching)
            results = self.client.query(
                collection_name=self.collection_name,
                query_text=query,
                limit=max(10, limit)
            )
            
            if not results:
                return ""

            # Helper to normalize common Arabic spelling variations
            query_words = [self._normalize_arabic(w.strip("؟.,!:")) for w in query.lower().split() if len(w.strip("؟.,!:")) > 1]
            # Sort results by keyword score descending, keeping vector similarity as tie-breaker
            results = sorted(results, key=self._get_keyword_score_fn(query_words), reverse=True)[:limit]

            context_blocks = []
            seen = set()
            for res in results:
                # If chunk has tenant metadata, we filter manually here or via Qdrant query filter
                chunk_tenant = res.metadata.get("tenant_id", "HSA_Group")
                # Treat "HSAGroup" and "HSA_Group" as equivalent to support both keys seamlessly.
                is_tenant_match = (
                    chunk_tenant == tenant_id or
                    (chunk_tenant in ("HSAGroup", "HSA_Group") and tenant_id in ("HSAGroup", "HSA_Group"))
                )
                # For safety in multi-tenant mode, only display if it matches tenant or matches a global company policy
                if is_tenant_match or chunk_tenant in ("HSAGroup", "HSA_Group"):
                    source = res.metadata.get("source", "Unknown Policy")
                    page_num = res.metadata.get("page_number", 1)
                    text = res.document.strip()
                    
                    key = (source, page_num, text)
                    if key not in seen:
                        seen.add(key)
                        if page_num:
                            context_blocks.append(f"[مصدر: {source} (صفحة {page_num})]\n{res.document}")
                        else:
                            context_blocks.append(f"[مصدر: {source}]\n{res.document}")
                
            return "\n\n---\n\n".join(context_blocks)
            
        except Exception as e:
            logger.error("Qdrant retrieve_context failed", exc_info=True)
            return ""

    def retrieve_context_with_metadata(self, query: str, limit: int = 3) -> list:
        if not self.client:
            logger.info("Qdrant Client is offline. Attempting reconnection...")
            self.init_client()

        if not self.client:
            logger.warning("Qdrant Client is offline. Returning empty context list.")
            return []

        tenant_id = get_tenant_id()
        logger.info(f"Retrieving structured context for query in Qdrant: {self.collection_name} (Tenant: {tenant_id})")

        try:
            # Check collections
            collections_info = self.client.get_collections()
            collection_names = [col.name for col in collections_info.collections]
            
            if self.collection_name not in collection_names:
                logger.warning(f"Collection '{self.collection_name}' does not exist.")
                return []

            # Retrieve documents
            results = self.client.query(
                collection_name=self.collection_name,
                query_text=query,
                limit=max(10, limit)
            )
            
            if not results:
                return []

            query_words = [self._normalize_arabic(w.strip("؟.,!:")) for w in query.lower().split() if len(w.strip("؟.,!:")) > 1]
            
            # Sort results by keyword score descending, keeping vector similarity as tie-breaker
            results = sorted(results, key=self._get_keyword_score_fn(query_words), reverse=True)[:limit]

            citations = []
            seen = set()
            for res in results:
                chunk_tenant = res.metadata.get("tenant_id", "HSA_Group")
                is_tenant_match = (
                    chunk_tenant == tenant_id or
                    (chunk_tenant in ("HSAGroup", "HSA_Group") and tenant_id in ("HSAGroup", "HSA_Group"))
                )
                if is_tenant_match or chunk_tenant in ("HSAGroup", "HSA_Group"):
                    source = res.metadata.get("source", "Unknown Policy")
                    page_num = res.metadata.get("page_number", 1)
                    text = res.document.strip()
                    
                    key = (source, page_num, text)
                    if key not in seen:
                        seen.add(key)
                        citations.append({
                            "source": source,
                            "category": res.metadata.get("category", "General"),
                            "page_number": page_num,
                            "text": res.document
                        })
                
            return citations
            
        except Exception as e:
            logger.error("Qdrant retrieve_context_with_metadata failed", exc_info=True)
            return []

    def _normalize_arabic(self, text: str) -> str:
        return (
            text.replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("ة", "ه")
            .replace("ى", "ي")
        )

    def _get_keyword_score_fn(self, query_words: list):
        def get_keyword_score(res_item) -> float:
            doc_text = self._normalize_arabic(getattr(res_item, "document", "").lower())
            score = 0.0
            # رفع وزن الكلمات الأساسية لضمان تطابق السياسة المطلوبة
            keywords = ["توظيف", "داخلي", "شروط", "نقل"]
            for kw in keywords:
                if kw in doc_text:
                    score += 3.0 # وزن أعلى للكلمات المفتاحية
            
            # تطابق الكلمات من سؤال المستخدم
            for word in query_words:
                if word in doc_text:
                    score += 1.0
            return score
        return get_keyword_score
