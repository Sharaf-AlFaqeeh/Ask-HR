import time
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

    Strategy (Rule-First):
      1. Always run rule-based NLP first (instant, ~0ms).
      2. If rule confidence >= threshold → accept immediately, skip LLM entirely.
      3. Only fall back to LLM for genuinely ambiguous queries (low confidence).

    This eliminates ~2-5 seconds of LLM latency on the vast majority of requests
    where keyword/regex patterns already produce a confident classification.

    Configurable modes via config.yaml `orchestrator.nlp_mode`:
      - "rule_first" (default): Rules primary, LLM fallback for ambiguous queries only.
      - "rule_only": Never call LLM for intent/entity analysis (fastest, no fallback).
      - "hybrid_always": Always run both engines and merge (legacy behavior, slowest).
    """

    VALID_MODES = {"rule_first", "rule_only", "hybrid_always"}

    def __init__(self, llm_client: ILLMClient):
        self.rule_nlp = RuleNLPAdapter()
        self.llm_nlp = LLMNLPAdapter(llm_client)
        self.confidence_threshold = settings.orchestrator.intent_confidence_threshold

        # Read NLP mode from config, default to "rule_first"
        raw_mode = getattr(settings.orchestrator, "nlp_mode", "rule_first")
        self.nlp_mode = raw_mode if raw_mode in self.VALID_MODES else "rule_first"

        logger.info(
            f"Hybrid NLP Pipeline initialized — mode={self.nlp_mode}, "
            f"confidence_threshold={self.confidence_threshold}"
        )

    async def analyze_query(self, query: str, has_pending_action: bool = False) -> Tuple[str, float, Dict[str, Any]]:
        """
        Executes intent classification and entity extraction.
        Rule-based engine runs first; LLM is invoked only when rules are ambiguous.
        """
        start = time.time()

        # ── Step 1: Always run rule-based analyzer (instant, synchronous) ──
        rule_intent, rule_conf, rule_entities = self.rule_nlp.analyze_query(query)
        rule_ms = (time.time() - start) * 1000

        logger.info(
            f"Rule NLP completed in {rule_ms:.1f}ms — "
            f"intent={rule_intent}, confidence={rule_conf:.2f}, entities={rule_entities}"
        )

        # ── Fast-exit paths (no LLM needed) ──

        # A. Active pending action → slot-filling relies on regex, skip LLM
        if has_pending_action:
            logger.info("Active pending action — using rule-based results only (slot filling).")
            return rule_intent, rule_conf, rule_entities

        # B. "rule_only" mode → never invoke LLM for NLP analysis
        if self.nlp_mode == "rule_only":
            logger.info("NLP mode is 'rule_only' — returning rule-based results.")
            return rule_intent, rule_conf, rule_entities

        # C. Rule-first mode: if rules are confident enough, skip LLM
        if self.nlp_mode == "rule_first" and rule_conf >= self.confidence_threshold:
            logger.info(
                f"Rule confidence {rule_conf:.2f} >= threshold {self.confidence_threshold} — "
                "skipping LLM NLP analysis."
            )
            return rule_intent, rule_conf, rule_entities

        # ── Step 2: LLM fallback (only for ambiguous / low-confidence queries) ──
        logger.info(
            f"Rule confidence {rule_conf:.2f} < threshold {self.confidence_threshold} — "
            "falling back to LLM semantic NLP analysis..."
        )
        llm_start = time.time()
        llm_intent, llm_conf, llm_entities = await self.llm_nlp.analyze_query_async(query)
        llm_ms = (time.time() - llm_start) * 1000

        logger.info(
            f"LLM NLP completed in {llm_ms:.1f}ms — "
            f"intent={llm_intent}, confidence={llm_conf:.2f}, entities={llm_entities}"
        )

        # ── Step 3: Smart merging ──
        # Prioritize regex-extracted entities (employee IDs, strict dates) as they
        # are 100% accurate; fall back to LLM entities for conversational values.
        merged_entities = {}
        for key in ["employee_id", "leave_type", "start_date", "end_date", "month"]:
            merged_entities[key] = rule_entities.get(key) or llm_entities.get(key)

        # Pick the higher-confidence intent
        final_intent = rule_intent
        final_conf = rule_conf
        if llm_conf > rule_conf:
            final_intent = llm_intent
            final_conf = llm_conf

        total_ms = (time.time() - start) * 1000
        logger.info(
            f"Hybrid NLP merged results ({total_ms:.1f}ms total): "
            f"intent={final_intent} ({final_conf:.2f}), entities={merged_entities}"
        )
        return final_intent, final_conf, merged_entities
