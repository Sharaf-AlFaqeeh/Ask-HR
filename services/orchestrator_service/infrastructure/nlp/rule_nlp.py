import re
from typing import Dict, Any, Tuple
from core.config_manager import get_settings
from core.logger import get_logger

logger = get_logger("rule_nlp_adapter")
settings = get_settings()

class RuleNLPAdapter:
    """
    NLP Adapter using fast, deterministic regular expressions and keyword heuristics
    to route intents and extract HR-specific business entities.
    """
    
    # Keywords for intent classification
    SAP_KEYWORDS = [
        "apply", "request", "submit", "book", "leave", "vacation", "sick leave", 
        "payslip", "salary slip", "salary", "pay slip", "slip",
        "طلب", "تقديم", "إجازة", "اجازه", "اجازة", "اجازتي", "رصيد", "مرضية", "مرضيه", "سنوية", "سنويه",
        "راتب", "كشف راتب", "كشف الراتب", "سليب", "الراتب", "خصم"
    ]
    
    RAG_KEYWORDS = [
        "policy", "rule", "guideline", "what is", "how many", "limit", "allowance", "benefits",
        "سياسة", "سياسه", "حقوق", "بدل", "بدلات", "قانون", "كم يوم", "شروط", "تأمين", "تأمين طبي"
    ]

    def analyze_query(self, query: str) -> Tuple[str, float, Dict[str, Any]]:
        q = query.lower()
        
        # 1. Intent Classification Heuristics
        sap_score = 0
        rag_score = 0

        for kw in self.SAP_KEYWORDS:
            if kw in q:
                sap_score += 1.5 if f" {kw} " in f" {q} " else 1.0

        for kw in self.RAG_KEYWORDS:
            if kw in q:
                rag_score += 1.5 if f" {kw} " in f" {q} " else 1.0

        action_prefixes = ["أريد", "ابغى", "ابغا", "قدم", "اطلب", "ارغب", "want to", "need to", "apply for"]
        has_action_prefix = False
        for pref in action_prefixes:
            if pref in q:
                sap_score += 1.0
                has_action_prefix = True

        # Informational indicators to boost RAG intent if no action is explicitly asked
        info_indicators = ["ما هي", "ما هو", "كيف", "شروط", "سياسة", "سياسه", "قانون", "هل", "كم", "what is", "how to", "policy"]
        if not has_action_prefix:
            for ind in info_indicators:
                if ind in q:
                    rag_score += 1.5

        total = sap_score + rag_score
        
        if total == 0:
            # Default fallback to RAG with neutral confidence
            intent = "RAG"
            confidence = 0.5
        else:
            confidence = max(sap_score, rag_score) / total
            intent = "SAP" if sap_score >= rag_score else "RAG"

        # 2. Entity Extraction Heuristics
        entities: Dict[str, Any] = {
            "employee_id": None,
            "leave_type": None,
            "start_date": None,
            "end_date": None,
            "month": None
        }

        # Employee ID extraction
        emp_match = re.search(r'\b(emp\d{3,6})\b', query, re.IGNORECASE)
        if emp_match:
            entities["employee_id"] = emp_match.group(1).upper()

        # Leave type extraction
        if any(w in q for w in ["مرضية", "مرضيه", "sick", "medical"]):
            entities["leave_type"] = "SICK_LEAVE"
        elif any(w in q for w in ["سنوية", "سنويه", "annual", "vacation"]):
            entities["leave_type"] = "ANNUAL_LEAVE"
        elif any(w in q for w in ["أمومة", "امومة", "وضع", "maternity"]):
            entities["leave_type"] = "MATERNITY_LEAVE"
        elif any(w in q for w in ["أبوة", "ابوة", "paternity"]):
            entities["leave_type"] = "PATERNITY_LEAVE"
        elif any(w in q for w in ["بدون راتب", "unpaid"]):
            entities["leave_type"] = "UNPAID_LEAVE"

        # Dates extraction (YYYY-MM-DD or DD/MM/YYYY with support for 1-2 digit months and days)
        date_pattern = r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b'
        dates = re.findall(date_pattern, query)
        
        def _normalize_date(date_str: str) -> str:
            normalized = date_str.replace('/', '-')
            parts = normalized.split('-')
            if len(parts) == 3:
                if len(parts[0]) == 4: # YYYY-MM-DD or YYYY-M-D
                    return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                elif len(parts[2]) == 4: # DD-MM-YYYY or D-M-YYYY
                    return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            return date_str

        if len(dates) >= 2:
            entities["start_date"] = _normalize_date(dates[0])
            entities["end_date"] = _normalize_date(dates[1])
        elif len(dates) == 1:
            entities["start_date"] = _normalize_date(dates[0])

        # Month extraction (Arabic and English)
        months_pattern = (
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december|'
            r'يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر|'
            r'may\s+\d{4}|مايو\s+\d{4})\b'
        )
        month_match = re.search(months_pattern, query, re.IGNORECASE)
        if month_match:
            entities["month"] = month_match.group(1).title()

        # Fallback employee_id default if 'emp' keyword matches but no number is present
        if not entities["employee_id"] and "emp" in q:
            entities["employee_id"] = "EMP101"

        logger.info(f"Rule NLP analysis: Intent={intent} ({confidence:.2f}), Entities={entities}")
        return intent, confidence, entities
