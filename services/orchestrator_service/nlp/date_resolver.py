import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from services.orchestrator_service.domain.interfaces import ILLMClient
from core.logger import get_logger

logger = get_logger("smart_date_resolver")


class SmartDateResolver:
    """
    Resolves natural language date expressions (Arabic & English) into concrete
    YYYY-MM-DD dates using LLM semantic analysis with rule-based fallback.
    
    Examples of supported expressions:
      - "غداً" / "بكرة" → tomorrow's date
      - "بعد 3 أيام" → today + 3
      - "الأسبوع القادم" → next Monday
      - "من 10 يوليو إلى 15 يوليو" → exact dates
      - "3 أيام من بكرة" → tomorrow to tomorrow+2
      - "يوم الأحد القادم" → next Sunday
    """

    DATE_RESOLVER_PROMPT = (
        "أنت محلل تواريخ دقيق لنظام الموارد البشرية.\n"
        "التاريخ الحالي (اليوم) هو: {today} ({today_weekday}).\n\n"
        "مهمتك: حلل نص المستخدم التالي واستخرج تاريخ بداية ونهاية الإجازة المطلوبة.\n\n"
        "القواعد الصارمة:\n"
        "1. أرجع JSON فقط بدون أي شرح أو markdown — فقط الكائن JSON.\n"
        "2. استخدم صيغة YYYY-MM-DD للتواريخ.\n"
        "3. إذا قال المستخدم 'غداً' أو 'بكرة' أو 'بكرا'، أضف يوماً واحداً على تاريخ اليوم.\n"
        "4. إذا قال 'بعد يومين'/'يومين'، أضف يومين. 'بعد أسبوع'/'أسبوع' أضف 7 أيام.\n"
        "5. إذا ذكر مدة (مثلاً '3 أيام' أو 'أسبوع') بدون تاريخ نهاية صريح، احسب تاريخ النهاية = تاريخ البداية + المدة - 1.\n"
        "6. إذا ذكر يوم أسبوع (مثلاً 'الأحد القادم')، احسب أقرب تاريخ قادم لهذا اليوم.\n"
        "7. إذا ذكر تاريخاً صريحاً بأرقام (مثلاً '10 يوليو' أو '2026-08-01')، استخدمه مباشرة. السنة الافتراضية هي {current_year}.\n"
        "8. إذا لم تستطع تحديد تاريخ بثقة، ضع null.\n"
        "9. إذا ذكر تاريخ بداية فقط بدون نهاية ولا مدة، ضع end_date = start_date (يوم واحد).\n\n"
        "الصيغة المطلوبة:\n"
        '{{\"start_date\": \"YYYY-MM-DD\" أو null, \"end_date\": \"YYYY-MM-DD\" أو null}}\n\n'
        "نص المستخدم: {user_text}"
    )

    # Arabic weekday names for prompt context
    WEEKDAY_NAMES_AR = [
        "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"
    ]

    # Quick regex patterns for common expressions (rule-based fast path)
    TOMORROW_PATTERNS = re.compile(
        r'\b(غدا|غداً|بكرة|بكرا|بكره|tomorrow)\b', re.IGNORECASE
    )
    TODAY_PATTERNS = re.compile(
        r'\b(اليوم|today)\b', re.IGNORECASE
    )
    DURATION_DAYS_PATTERN = re.compile(
        r'(\d+)\s*(?:أيام|ايام|يوم|days?)\b', re.IGNORECASE
    )
    EXPLICIT_DATE_PATTERN = re.compile(
        r'\b(\d{4}[-/]\d{2}[-/]\d{2})\b'
    )

    def _try_rule_based(self, user_text: str, today: datetime) -> Optional[Dict[str, Any]]:
        """
        Attempts fast rule-based date resolution for simple, unambiguous expressions.
        Returns None if the expression is too complex for rules.
        """
        text = user_text.strip()
        
        # Check for explicit YYYY-MM-DD dates first
        explicit_dates = self.EXPLICIT_DATE_PATTERN.findall(text)
        if len(explicit_dates) >= 2:
            return {
                "start_date": explicit_dates[0].replace("/", "-"),
                "end_date": explicit_dates[1].replace("/", "-"),
                "inferred": False
            }
        if len(explicit_dates) == 1:
            start = explicit_dates[0].replace("/", "-")
            # Check if there's a duration mentioned
            dur_match = self.DURATION_DAYS_PATTERN.search(text)
            if dur_match:
                days = int(dur_match.group(1))
                try:
                    start_dt = datetime.strptime(start, "%Y-%m-%d")
                    end_dt = start_dt + timedelta(days=max(days - 1, 0))
                    return {
                        "start_date": start,
                        "end_date": end_dt.strftime("%Y-%m-%d"),
                        "inferred": True
                    }
                except ValueError:
                    pass
            return {
                "start_date": start,
                "end_date": start,
                "inferred": False
            }

        # Check for "tomorrow" + optional duration
        if self.TOMORROW_PATTERNS.search(text):
            start_dt = today + timedelta(days=1)
            dur_match = self.DURATION_DAYS_PATTERN.search(text)
            if dur_match:
                days = int(dur_match.group(1))
                end_dt = start_dt + timedelta(days=max(days - 1, 0))
            else:
                end_dt = start_dt
            return {
                "start_date": start_dt.strftime("%Y-%m-%d"),
                "end_date": end_dt.strftime("%Y-%m-%d"),
                "inferred": True
            }

        # Check for "today" + optional duration
        if self.TODAY_PATTERNS.search(text):
            start_dt = today
            dur_match = self.DURATION_DAYS_PATTERN.search(text)
            if dur_match:
                days = int(dur_match.group(1))
                end_dt = start_dt + timedelta(days=max(days - 1, 0))
            else:
                end_dt = start_dt
            return {
                "start_date": start_dt.strftime("%Y-%m-%d"),
                "end_date": end_dt.strftime("%Y-%m-%d"),
                "inferred": True
            }

        # If no clear pattern matched, return None to fall through to LLM
        return None

    async def resolve(
        self,
        user_text: str,
        llm_client: ILLMClient,
        reference_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Resolves natural language date expressions to concrete YYYY-MM-DD dates.
        
        Args:
            user_text: The original user query text.
            llm_client: The LLM client for semantic analysis.
            reference_date: Optional override for "today" (for testing).
            
        Returns:
            Dict with keys: start_date, end_date (both str|None), inferred (bool).
        """
        today = reference_date or datetime.now()
        today_str = today.strftime("%Y-%m-%d")

        # ── Fast path: try rule-based resolution first ──
        rule_result = self._try_rule_based(user_text, today)
        if rule_result is not None:
            logger.info(
                f"Date resolved via rules: start={rule_result['start_date']}, "
                f"end={rule_result['end_date']}, inferred={rule_result['inferred']}"
            )
            return rule_result

        # ── Slow path: LLM semantic analysis ──
        logger.info(f"Rule-based date resolution failed, falling back to LLM for: '{user_text}'")
        
        today_weekday = self.WEEKDAY_NAMES_AR[today.weekday()]
        prompt = self.DATE_RESOLVER_PROMPT.format(
            today=today_str,
            today_weekday=today_weekday,
            current_year=today.year,
            user_text=user_text
        )

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text}
        ]

        try:
            response_text = await llm_client.query_llm(messages, temperature=0.0, max_tokens=128)
            logger.info(f"LLM date resolver raw response: {response_text}")

            parsed = self._parse_json_response(response_text)
            start_date = parsed.get("start_date")
            end_date = parsed.get("end_date")

            # Validate date formats
            if start_date:
                self._validate_date_format(start_date)
            if end_date:
                self._validate_date_format(end_date)

            # If start exists but no end, default end = start
            if start_date and not end_date:
                end_date = start_date

            result = {
                "start_date": start_date,
                "end_date": end_date,
                "inferred": start_date is not None
            }
            logger.info(
                f"Date resolved via LLM: start={result['start_date']}, "
                f"end={result['end_date']}"
            )
            return result

        except Exception as e:
            logger.error(f"LLM date resolution failed: {e}", exc_info=True)
            return {"start_date": None, "end_date": None, "inferred": False}

    def _validate_date_format(self, date_str: str) -> None:
        """Raises ValueError if date_str is not valid YYYY-MM-DD."""
        datetime.strptime(date_str, "%Y-%m-%d")

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Extracts JSON from LLM response, handling markdown wrapping."""
        cleaned = text.strip()
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end + 1]
        return json.loads(cleaned)
