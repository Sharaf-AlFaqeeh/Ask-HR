import re
import random
from typing import Optional, List, Dict, Any
from core.logger import get_logger
from services.orchestrator_service.nlp.fast_response_filter import normalize_arabic, FastResponseFilter

logger = get_logger("feedback_filter")

class FeedbackFilter:
    """
    Filter to intercept feedback/acknowledgements and contextual follow-up/interrogative queries.
    """
    def __init__(self):
        # Acknowledgement / feedback terms
        raw_arabic_feedback = {
            "نعم", "شكرا", "شكرًا", "شكرا لك", "شكرًا لك", "تسلم", "تسلم دياتك", "يعطيك العافية", "يعطيك العافيه", 
            "مشكور", "مشكور جدا", "جزاك الله خيرا", "جزاك الله خير", "نعم شكرا", "نعم شكرًا",
            "ممتاز", "احسنت", "اوكي", "ok", "تمام", "واضح", "جميل", "رائع", "موافق", "ماشي", "طيب", "حسنا",
            "ممتاز جدا", "تمام شكرا", "واضح جدا", "جميل جدا", "رائع جدا", "حسنا شكرا", "واضح شكرا", "واضح شكرًا"
        }
        self._arabic_feedback = {normalize_arabic(f) for f in raw_arabic_feedback}

        raw_english_feedback = {
            "ok", "okay", "perfect", "great", "awesome", "well done", "nice", "cool", "got it", "clear",
            "thank you", "thanks", "yes", "yes thank you", "yes thanks", "yep", "yeah", "correct", "indeed",
            "sure", "right", "thank you so much", "thanks a lot"
        }
        self._english_feedback = {FastResponseFilter._normalize_english(f) for f in raw_english_feedback}

        self._arabic_responses = [
            "يسعدني أن الأمور واضحة لك! هل هناك أي شيء آخر يمكنني مساعدتك به؟ 😊",
            "على الرحب والسعة! في خدمتك دائماً لأي استفسار آخر.",
            "بالخدمة دائماً! أتمنى لك يوماً سعيداً."
        ]
        self._english_responses = [
            "Glad to hear that is clear! Let know if you have any other questions. 😊",
            "Awesome! I'm here if you need anything else.",
            "Perfect! Have a great day, and feel free to ask more questions."
        ]

        # General question particles
        raw_arabic_particles = {
            "لم افهم","لماذا", "ما فهمت","مافهمت","لم أفهم","كيف", "متى", "اين", "من", "شروطها", "بين", "وضح", "تفاصيل", "ماذا تعني", "ما المعنى", 
            "لماذا ذلك", "كيف ذلك", "وشروطها", "تفاصيلها","بينها","وضحها", "وضح اكثر", "وضح ذلك", "ما السبب", "ما سبب"
        }
        self._arabic_particles = {normalize_arabic(p) for p in raw_arabic_particles}

        raw_english_particles = {
            "why", "how", "when", "where", "who", "details", "explain", "what does it mean", "what do you mean",
            "why is that", "explain more", "explain that"
        }
        self._english_particles = {FastResponseFilter._normalize_english(p) for p in raw_english_particles}

    def match_feedback(self, query: str, history: Optional[List[Any]] = None) -> Optional[str]:
        """
        If the query is a simple acknowledgement/feedback word, returns a polite response.
        """
        if not query:
            return None
        
        # Check if the last assistant message was a question
        if history:
            last_assistant_msg = None
            for msg in reversed(history):
                if msg.role == "assistant":
                    last_assistant_msg = msg.content
                    break
            if last_assistant_msg:
                trimmed = last_assistant_msg.strip()
                is_question = trimmed.endswith("؟") or trimmed.endswith("?") or trimmed.startswith("هل")
                if is_question:
                    # Do not intercept standard confirmations so they pass to LLM
                    is_en = FastResponseFilter._is_english(query)
                    if is_en:
                        normalized = FastResponseFilter._normalize_english(query)
                        if normalized in {"ok", "okay", "yes", "no", "agree", "confirm"}:
                            return None
                    else:
                        normalized = normalize_arabic(query)
                        if normalized in {"نعم", "لا", "موافق", "تاكيد", "اوكي", "تمام"}:
                            return None

        is_en = FastResponseFilter._is_english(query)
        if is_en:
            normalized = FastResponseFilter._normalize_english(query)
            if normalized in self._english_feedback:
                return random.choice(self._english_responses)
        else:
            normalized = normalize_arabic(query)
            if normalized in self._arabic_feedback:
                return random.choice(self._arabic_responses)
        return None

    def match_followup(self, query: str, history: List[Any]) -> Optional[str]:
        """
        Detects if the query keyword/value exists in the last assistant response,
        or matches a general question/follow-up particle.
        If so, returns a reformulated/enriched query contextually.
        """
        if not query or not history:
            return None

        # 1. Find last assistant message
        last_assistant_msg = None
        for msg in reversed(history):
            if msg.role == "assistant":
                last_assistant_msg = msg.content
                break

        if not last_assistant_msg:
            return None

        # 2. Check if query is short (e.g. <= 3 words or <= 25 characters)
        words = query.strip().split()
        if len(words) > 3 or len(query) > 25:
            return None

        # 3. Clean and normalize query and assistant message
        is_en = FastResponseFilter._is_english(query)
        clean_query = query.replace("?", "").replace("؟", "").strip()
        
        if is_en:
            norm_query = FastResponseFilter._normalize_english(clean_query)
            norm_assistant = FastResponseFilter._normalize_english(last_assistant_msg)
        else:
            norm_query = normalize_arabic(clean_query)
            norm_assistant = normalize_arabic(last_assistant_msg)

        # 4. Check if the query matches a particle or exists in the last assistant response
        is_keyword_match = len(norm_query) >= 2 and norm_query in norm_assistant
        is_particle_match = norm_query in (self._english_particles if is_en else self._arabic_particles)

        if not (is_keyword_match or is_particle_match):
            return None

        # 5. Formulate rewritten query using last assistant response (first 250 chars) as context
        logger.info(f"FeedbackFilter detected contextual follow-up: query='{query}', is_keyword={is_keyword_match}, is_particle={is_particle_match}")
        
        context_snippet = last_assistant_msg[:250].strip()
        # Add ellipsis if truncated
        if len(last_assistant_msg) > 250:
            context_snippet += "..."

        if is_en:
            return f"Explain {clean_query} in the context of the previous response: {context_snippet}"
        else:
            return f"توضيح حول {clean_query} في سياق الإجابة السابقة: {context_snippet}"
