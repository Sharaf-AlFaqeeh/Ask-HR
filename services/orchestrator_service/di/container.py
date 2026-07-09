from services.orchestrator_service.infrastructure.llm_clients.openai_client import OpenAICompatibleLLMClient
from services.orchestrator_service.infrastructure.rag.qdrant_retriever import QdrantRetrieverAdapter
from services.orchestrator_service.infrastructure.hr_systems.sap_client import SAPSuccessFactorsAdapter
from services.orchestrator_service.domain.interfaces import ISessionStore
from services.orchestrator_service.infrastructure.nlp.hybrid_nlp import HybridNLPPipeline
from services.orchestrator_service.nlp.fast_response_filter import FastResponseFilter
from services.orchestrator_service.application.flow_orchestrator import FlowOrchestrator
from core.logger import get_logger

logger = get_logger("dependency_injection_container")

class DIContainer:
    """
    Dependency Injection Container.
    Initializes and wires adapters to ports, exposing configured services as singletons.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DIContainer, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        logger.info("Initializing DI Container and wiring enterprise dependencies...")
        
        # 1. Load Settings
        from core.config_manager import get_settings
        settings = get_settings()
        
        # 2. Instantiate Adapters
        self.llm_client = OpenAICompatibleLLMClient()
        self.retriever = QdrantRetrieverAdapter()
        self.hr_client = SAPSuccessFactorsAdapter()
        
        # Initialize selected Session Store
        self.session_store: ISessionStore
        storage_type = settings.storage.type.lower()
        if storage_type == "redis":
            from services.orchestrator_service.infrastructure.storage.redis_store import RedisSessionStore
            logger.info(f"Wiring RedisSessionStore adapter to host={settings.storage.redis.host}:{settings.storage.redis.port}")
            self.session_store = RedisSessionStore(
                host=settings.storage.redis.host,
                port=settings.storage.redis.port,
                db=settings.storage.redis.db,
                password=settings.storage.redis.password,
                ttl=settings.storage.session_ttl
            )
        elif storage_type == "in_memory":
            from services.orchestrator_service.infrastructure.storage.in_memory import InMemorySessionStore
            logger.info("Wiring InMemorySessionStore adapter...")
            self.session_store = InMemorySessionStore()
        else:
            from services.orchestrator_service.infrastructure.storage.sqlite_store import SQLiteSessionStore
            logger.info("Wiring SQLiteSessionStore adapter...")
            self.session_store = SQLiteSessionStore()
        
        # 3. Instantiate NLP Pipeline (passing LLM Client for semantic fallback)
        self.nlp_pipeline = HybridNLPPipeline(self.llm_client)
        
        # Instantiate Fast Response Filter
        self.fast_response_filter = FastResponseFilter()
        
        # Instantiate Feedback and Follow-up Filter
        from services.orchestrator_service.nlp.feedback_filter import FeedbackFilter
        self.feedback_filter = FeedbackFilter()
        
        # 3. Instantiate and wire FlowOrchestrator
        self.flow_orchestrator = FlowOrchestrator(
            llm_client=self.llm_client,
            retriever=self.retriever,
            hr_client=self.hr_client,
            session_store=self.session_store,
            nlp_pipeline=self.nlp_pipeline,
            fast_response_filter=self.fast_response_filter,
            feedback_filter=self.feedback_filter
        )
        
        self._initialized = True
        logger.info("DI Container wired successfully.")

# Global instance provider
_container = None

def get_container() -> DIContainer:
    global _container
    if _container is None:
        _container = DIContainer()
    return _container
