import json
import re
from typing import Dict, Any, Tuple, Optional
from services.orchestrator_service.domain.interfaces import ILLMClient
from core.logger import get_logger

logger = get_logger("llm_nlp_adapter")

class LLMNLPAdapter:
    """
    NLP Adapter using LLM zero-shot semantic analysis to classify intents
    and extract complex entity values from conversational text.
    """
    def __init__(self, llm_client: ILLMClient):
        self.llm_client = llm_client

    async def analyze_query_async(self, query: str) -> Tuple[str, float, Dict[str, Any]]:
        logger.info(f"Running LLM semantic NLP analysis for query: '{query}'")
        
        system_instruction = (
            "You are an expert NLP parser for a Corporate HR system.\n"
            "Analyze the user's HR query and output ONLY a valid JSON object matching this schema:\n"
            "{\n"
            "  \"intent\": \"SAP\" or \"RAG\",\n"
            "  \"confidence\": float (0.0 to 1.0),\n"
            "  \"entities\": {\n"
            "    \"employee_id\": string or null,\n"
            "    \"leave_type\": \"ANNUAL_LEAVE\" | \"SICK_LEAVE\" | \"MATERNITY_LEAVE\" | \"PATERNITY_LEAVE\" | \"UNPAID_LEAVE\" | null,\n"
            "    \"start_date\": \"YYYY-MM-DD\" or null,\n"
            "    \"end_date\": \"YYYY-MM-DD\" or null,\n"
            "    \"month\": string (e.g. \"May 2026\", \"مايو\") or null\n"
            "  }\n"
            "}\n\n"
            "Rules:\n"
            "- Set intent to \"SAP\" if the user wants to execute an action (e.g. submit leave request, request payslip, get profile info).\n"
            "- Set intent to \"RAG\" if the user is asking a general policy question (e.g. 'How many leave days?', 'What is housing allowance?').\n"
            "- Do NOT include any markdown block ticks (like ```json), introduction, or explanations. Only return the raw JSON string."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Query: {query}"}
        ]

        try:
            # Query LLM (using low temperature for deterministic parsing output)
            response_text = await self.llm_client.query_llm(messages, temperature=0.0)
            logger.info(f"LLM NLP Raw Response: {response_text}")
            
            # Clean and parse output
            parsed_data = self._clean_and_parse_json(response_text)
            
            intent = parsed_data.get("intent", "RAG")
            confidence = float(parsed_data.get("confidence", 0.7))
            entities = parsed_data.get("entities", {})
            
            # Sanity-clean entities dictionary keys
            cleaned_entities = {
                "employee_id": entities.get("employee_id"),
                "leave_type": entities.get("leave_type"),
                "start_date": entities.get("start_date"),
                "end_date": entities.get("end_date"),
                "month": entities.get("month")
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
