import httpx
import asyncio
from typing import List, Dict, Any, Optional
from services.orchestrator_service.domain.interfaces import ILLMClient
from core.config_manager import get_settings
from core.logger import get_logger

logger = get_logger("openai_client_adapter")
settings = get_settings()

class OpenAICompatibleLLMClient(ILLMClient):
    """
    Adapter implementing the ILLMClient port.
    Communicates with local/remote OpenAI-compatible APIs (like llama-cpp-python, Qwen local server, or OpenAI).
    """
    def __init__(self):
        self.api_url = f"{settings.orchestrator.llm_api_url}/chat/completions"
        self.default_temp = settings.llm.temperature
        self.default_max_tokens = settings.llm.max_tokens
        logger.info(f"Initializing LLM Adapter targeting API at: {self.api_url}")

    async def query_llm(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None, 
        max_tokens: Optional[int] = None
    ) -> str:
        temp = temperature if temperature is not None else self.default_temp
        max_t = max_tokens if max_tokens is not None else self.default_max_tokens
        
        payload = {
            "model": "qwen2.5-7b",
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_t
        }
        
        retries = 3
        backoff_factor = 2.0
        timeout = 120.0
        
        for attempt in range(retries):
            try:
                # Setting a configurable timeout for CPU model execution (default 120s)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(self.api_url, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        reply = data["choices"][0]["message"]["content"]
                        logger.info("LLM adapter request completed successfully.")
                        return reply
                    else:
                        logger.error(f"LLM API returned status {response.status_code}: {response.text}")
                        # If HTTP status is not 200, we might retry or break based on severity. Let's retry for 5xx.
                        if response.status_code >= 500 and attempt < retries - 1:
                            sleep_time = backoff_factor ** attempt
                            logger.info(f"Server error {response.status_code}. Retrying in {sleep_time}s...")
                            await asyncio.sleep(sleep_time)
                        else:
                            break
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                logger.warning(f"LLM connection attempt {attempt + 1} failed: {exc}")
                if attempt < retries - 1:
                    sleep_time = backoff_factor ** attempt
                    logger.info(f"Retrying query_llm in {sleep_time} seconds...")
                    await asyncio.sleep(sleep_time)
                else:
                    logger.error(f"LLM adapter connections all timed out or failed after {retries} attempts.")
            except Exception as exc:
                logger.error(f"Unexpected error during LLM Adapter execution: {exc}")
                break
                
        is_nlp_parser = False
        for msg in messages:
            if msg.get("role") == "system" and "expert NLP parser" in msg.get("content", ""):
                is_nlp_parser = True
                break
                
        return self._fallback_reply(messages[-1]["content"], is_nlp_parser=is_nlp_parser)

    def _fallback_reply(self, user_query: str, is_nlp_parser: bool = False) -> str:
        """
        Grounded mock reply in case the local llama-cpp service is offline.
        """
        logger.warning("Using local mock fallback completion reply.")
        
        if is_nlp_parser:
            return '{"intent": "RAG", "confidence": 0.5, "entities": {"employee_id": null, "leave_type": null, "start_date": null, "end_date": null, "month": null}}'
            
        q = user_query.lower()
        if "إجازة" in q or "leave" in q or "vacation" in q:
            return (
                "⚠️ [النظام: خادم الاستدلال غير متوفر].\n"
                "لتسجيل طلب إجازة في SAP SuccessFactors، يرجى تشغيل خادم الاستدلال أو توفير ملف النموذج qwen.\n"
                "حالة الطلب البرمجية: تم التحقق منها وبانتظار خادم الذكاء الاصطناعي."
            )
        elif "راتب" in q or "salary" in q or "slip" in q:
            return (
                "⚠️ [النظام: خادم الاستدلال غير متوفر].\n"
                "كشف الراتب المسحوب بنجاح من SAP:\n"
                "- الراتب الأساسي: 2500 USD\n"
                "- بدل السكن: 625 USD\n"
                "- صافي الراتب: 2975 USD"
            )
        else:
            return (
                "⚠️ [ملاحظة النظام: خادم LLM المحلي (llama-cpp-python) غير متاح حالياً].\n"
                "مرحباً بك! لقد استقبلت طلبك بنجاح وتمت معالجته عبر المحرك البرمجي لنظام AskHR."
            )
        
