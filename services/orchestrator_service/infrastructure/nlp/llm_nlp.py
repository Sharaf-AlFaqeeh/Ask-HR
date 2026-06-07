import json
import re
from typing import Dict, Any, Tuple, Optional
from services.orchestrator_service.domain.interfaces import ILLMClient
from services.orchestrator_service.application.prompt_registry import PromptRegistry
from core.logger import get_logger

logger = get_logger("llm_nlp_adapter")

class LLMNLPAdapter:
    """
    NLP Adapter using LLM zero-shot semantic analysis to classify intents
    and extract complex entity values from conversational text.
    """
    def __init__(self, llm_client: ILLMClient):
        self.llm_client = llm_client

    TEMPORAL_KEYWORDS = {
        # English relative/temporal terms
        "today", "tomorrow", "yesterday", "next", "last", "day", "week", "month", "year",
        "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
        "mon", "tue", "wed", "thu", "fri", "sat", "sun", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        # Arabic relative/temporal terms
        "اليوم", "بكرة", "بكرا", "غدا", "غداً", "أمس", "الامس", "يوم", "يومين", "أيام", "ايام", "اسبوع", "أسبوع",
        "اسابيع", "أسابيع", "شهر", "شهور", "أشهر", "اشهر", "سنة", "سنوات", "أعوام", "اعوام", "عام",
        "يناير", "فبراير", "مارس", "أبريل", "ابريل", "مايو", "يونيو", "يوليو", "أغسطس", "اغسطس", "سبتمبر", "أكتوبر", "اكتوبر", "نوفمبر", "ديسمبر",
        "السبت", "الأحد", "الاحد", "الاثنين", "الثلاثاء", "الأربعاء", "الاربعاء", "الخميس", "الجمعة", "الجمعه",
        "القادم", "المقبل", "الماضي", "السابق", "منذ", "خلال", "بعد", "قبل"
    }

    def _validate_temporal_entity(self, query: str, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        # Normalize comparison
        q_lower = query.lower()
        val_str = str(value).lower()
        if val_str in q_lower:
            return value
        # Check if query contains any digits (Western or Arabic-Indic)
        if re.search(r'[0-9\u0660-\u0669]', query):
            return value
        # Tokenize query and check intersection with temporal keywords
        words = set(re.findall(r'\w+', q_lower))
        if words.intersection(self.TEMPORAL_KEYWORDS):
            return value
        logger.warning(f"Validation failed for LLM-extracted entity: '{value}' in query '{query}'. Nullifying to prevent hallucination.")
        return None

    async def analyze_query_async(self, query: str) -> Tuple[str, float, Dict[str, Any]]:
        logger.info(f"Running LLM semantic NLP analysis for query: '{query}'")
        
        system_instruction = PromptRegistry.NLP_PARSER_SYSTEM

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Query: {query}"}
        ]

        try:
            # Query LLM (using low temperature and lower max_tokens for deterministic parsing output)
            response_text = await self.llm_client.query_llm(messages, temperature=0.0, max_tokens=256)
            logger.info(f"LLM NLP Raw Response: {response_text}")
            
            # Clean and parse output
            parsed_data = self._clean_and_parse_json(response_text)
            
            intent = parsed_data.get("intent", "RAG")
            confidence = float(parsed_data.get("confidence", 0.7))
            entities = parsed_data.get("entities", {})
            
            # Extract and validate dates/month to prevent hallucinations
            start_date = self._validate_temporal_entity(query, entities.get("start_date"))
            end_date = self._validate_temporal_entity(query, entities.get("end_date"))
            month = self._validate_temporal_entity(query, entities.get("month"))

            # Sanity-clean entities dictionary keys
            cleaned_entities = {
                "employee_id": entities.get("employee_id"),
                "leave_type": entities.get("leave_type"),
                "start_date": start_date,
                "end_date": end_date,
                "month": month
            }
            
            return intent, confidence, cleaned_entities
            
        except Exception as e:
            logger.error("LLM NLP analysis failed, using fallback empty values", exc_info=True)
            return "RAG", 0.5, {
                "employee_id": None, "leave_type": None, "start_date": None, "end_date": None, "month": None
            }

    def _clean_and_parse_json(self, text: str) -> Dict[str, Any]:
        """
        Extracts and parses JSON payload even if wrapped in markdown formatting.
        """
        cleaned = text.strip()
        # Remove code blocks
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
                
        # Find first '{' and last '}'
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end+1]
            
        return json.loads(cleaned)
