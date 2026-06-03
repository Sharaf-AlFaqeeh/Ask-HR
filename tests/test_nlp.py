import pytest
from services.orchestrator_service.infrastructure.nlp.rule_nlp import RuleNLPAdapter

def test_rule_nlp_leave_extraction():
    nlp = RuleNLPAdapter()
    query = "أريد تقديم إجازة سنوية للموظف emp102 من 2026-06-01 إلى 2026-06-15"
    intent, confidence, entities = nlp.analyze_query(query)
    
    assert intent == "SAP"
    assert entities["employee_id"] == "EMP102"
    assert entities["leave_type"] == "ANNUAL_LEAVE"
    assert entities["start_date"] == "2026-06-01"
    assert entities["end_date"] == "2026-06-15"

def test_rule_nlp_payslip_extraction():
    nlp = RuleNLPAdapter()
    query = "احضر لي كشف الراتب للموظف emp101 لشهر مايو 2026"
    intent, confidence, entities = nlp.analyze_query(query)
    
    assert intent == "SAP"
    assert entities["employee_id"] == "EMP101"
    assert entities["month"] is not None

def test_rule_nlp_rag_intent():
    nlp = RuleNLPAdapter()
    query = "ما هي سياسة بدلات السكن في HSA Group؟"
    intent, confidence, entities = nlp.analyze_query(query)
    
    assert intent == "RAG"
