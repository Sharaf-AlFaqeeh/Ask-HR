import os
import sys
from typing import Dict, Any, Tuple

# Adjust path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from core.logger import get_logger
from core.config_manager import get_settings

logger = get_logger("intent_router")
settings = get_settings()

class IntentRouter:
    """
    Analyzes user queries to route them to the correct backend execution engine:
    - 'RAG': Queries about HR rules, benefits, guidelines.
    - 'SAP': Requests to perform action (e.g. submit leave, view payslip).
    """
    
    # Keyword list for intent heuristic routing (supports Arabic and English)
    SAP_KEYWORDS = [
        # English keywords
        "apply", "request", "submit", "book", "leave", "vacation", "sick leave", 
        "payslip", "salary slip", "salary", "pay slip", "slip",
        # Arabic keywords
        "طلب", "تقديم", "إجازة", "اجازه", "مرضية", "مرضيه", "سنوية", "سنويه",
        "راتب", "كشف راتب", "كشف الراتب", "سليب", "الراتب", "خصم", "بدل"
    ]
    
    RAG_KEYWORDS = [
        # English keywords
        "policy", "rule", "guideline", "what is", "how many", "limit", "allowance", "benefits",
        # Arabic keywords
        "سياسة", "سياسه", "حقوق", "بدلات", "قانون", "كم يوم", "شروط", "تأمين", "تأمين طبي"
    ]

    def route_intent(self, query: str) -> Tuple[str, float]:
        """
        Determines the intent classification and confidence score.
        Returns: Tuple[intent_name ('RAG' | 'SAP'), confidence_score (0.0 to 1.0)]
        """
        q = query.lower()
        logger.info(f"Routing intent for query: '{query}'")

        sap_score = 0
        rag_score = 0

        # Heuristic 1: Keyword exact & partial matching
        for kw in self.SAP_KEYWORDS:
            if kw in q:
                sap_score += 1.5 if f" {kw} " in f" {q} " else 1.0

        for kw in self.RAG_KEYWORDS:
            if kw in q:
                rag_score += 1.5 if f" {kw} " in f" {q} " else 1.0

        # Heuristic 2: Action vs Informational patterns
        # Arabic Action Verbs: "أريد تقديم"، "كيف أطلب"، "أبغا إجازة"
        action_prefixes = ["أريد", "ابغى", "ابغا", "قدم", "اطلب", "ارغب", "want to", "need to", "apply for"]
        for pref in action_prefixes:
            if pref in q:
                sap_score += 1.0

        # Calculate final confidence scores
        total = sap_score + rag_score
        if total == 0:
            # Default to RAG (information retrieval) with low confidence
            logger.info("No matching keywords. Defaulting intent to RAG.")
            return "RAG", 0.5
            
        confidence = max(sap_score, rag_score) / total
        intent = "SAP" if sap_score >= rag_score else "RAG"

        # Apply confidence thresholds
        threshold = settings.orchestrator.intent_confidence_threshold
        if confidence < threshold:
            logger.warning(
                f"Confidence {confidence:.2f} is below threshold {threshold}. "
                "Applying default fallback rules."
            )

        logger.info(f"Intent classified: {intent} (Confidence: {confidence:.2f})")
        return intent, confidence
