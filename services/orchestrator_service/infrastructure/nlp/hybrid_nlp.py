from typing import Dict, Any, Tuple
from services.orchestrator_service.domain.interfaces import INLPPipeline, ILLMClient
from services.orchestrator_service.infrastructure.nlp.rule_nlp import RuleNLPAdapter
from services.orchestrator_service.infrastructure.nlp.llm_nlp import LLMNLPAdapter
from core.logger import get_logger
from core.config_manager import get_settings

logger = get_logger("hybrid_nlp_pipeline")
settings = get_settings()

class HybridNLPPipeline(INLPPipeline):
    """
    Adapter implementing the INLPPipeline port.
    Combines rule-based regex extraction (fast, 100% accurate for formatting)
    with LLM semantic parsing (flexible, captures context) in an async hybrid pipeline.
    """
    def __init__(self, llm_client: ILLMClient):
        self.rule_nlp = RuleNLPAdapter()
        self.llm_nlp = LLMNLPAdapter(llm_client)
        self.confidence_threshold = settings.orchestrator.intent_confidence_threshold
        logger.info(f"Hybrid NLP Pipeline initialized (Threshold: {self.confidence_threshold})")

    async def analyze_query(self, query: str) -> Tuple[str, float, Dict[str, Any]]:
        """
        Executes hybrid classification: Rules first, falling back to LLM if needed.
        """
        # 1. Run rule-based analyzer synchronously
        rule_intent, rule_conf, rule_entities = self.rule_nlp.analyze_query(query)

        # 2. If rules are highly confident and have resolved the employee ID, we can skip LLM parsing to save resources
        if rule_conf >= 0.9 and rule_entities.get("employee_id") is not None:
            logger.info("Rule-based analysis has high confidence and resolved employee_id. Skipping LLM NLP parsing.")
            return rule_intent, rule_conf, rule_entities

        # 3. Otherwise, run LLM semantic analysis
        logger.info("Executing LLM semantic NLP analysis...")
        llm_intent, llm_conf, llm_entities = await self.llm_nlp.analyze_query_async(query)

        # 4. Smart merging:
        # - Prioritize regex-extracted entities (e.g. employee IDs, strict dates) as they are 100% accurate.
        # - Fallback to LLM entities for conversational values.
        merged_entities = {}
        for key in ["employee_id", "leave_type", "start_date", "end_date", "month"]:
            merged_entities[key] = rule_entities.get(key) or llm_entities.get(key)

        # Determine final intent: if rules have strong keywords, prioritize rules; otherwise use LLM
        final_intent = rule_intent
        final_conf = rule_conf
        
        if llm_conf > rule_conf:
            final_intent = llm_intent
            final_conf = llm_conf
            
        logger.info(f"Hybrid NLP merged results: Intent={final_intent} ({final_conf:.2f}), Entities={merged_entities}")
        return final_intent, final_conf, merged_entities
