import pytest
from unittest.mock import AsyncMock
from services.orchestrator_service.application.prompt_registry import PromptRegistry
from services.orchestrator_service.application.response_templates import ResponseTemplates
from services.orchestrator_service.infrastructure.nlp.llm_nlp import LLMNLPAdapter
from services.orchestrator_service.infrastructure.nlp.hybrid_nlp import HybridNLPPipeline

def test_prompt_registry_formatting():
    # Verify PromptRegistry templates format correctly
    formatted_leave = PromptRegistry.SAP_REQUEST_LEAVE_USER.format(
        request_id="LR-100",
        employee_id="EMP123",
        leave_type="ANNUAL_LEAVE",
        start_date="2026-06-01",
        end_date="2026-06-10",
        status="APPROVED",
        message="Request approved"
    )
    assert "LR-100" in formatted_leave
    assert "EMP123" in formatted_leave
    assert "ANNUAL_LEAVE" in formatted_leave

def test_response_templates_output():
    # Verify ResponseTemplates outputs correct Arabic strings
    res_leave = ResponseTemplates.get_leave_response(
        request_id="LR-101",
        employee_id="EMP99",
        leave_type="SICK_LEAVE",
        start_date="2026-06-01",
        end_date="2026-06-05",
        status="PENDING",
        message="Pending approval"
    )
    assert "LR-101" in res_leave
    assert "EMP99" in res_leave
    assert "إجازة مرضية" in res_leave
    assert "PENDING" in res_leave

    res_salary = ResponseTemplates.get_salary_slip_response(
        employee_id="EMP99",
        month="May 2026",
        basic_salary=3000.0,
        housing_allowance=750.0,
        transport_allowance=300.0,
        deductions=50.0,
        net_salary=4000.0
    )
    assert "May 2026" in res_salary
    assert "3000.0" in res_salary
    assert "4000.0" in res_salary

def test_temporal_entity_validation():
    # Mock LLM client to init adapter
    mock_llm = AsyncMock()
    adapter = LLMNLPAdapter(mock_llm)

    # Case 1: Date is present literally in the query -> preserve
    q1 = "أريد إجازة من 2026-06-01 إلى 2026-06-15"
    assert adapter._validate_temporal_entity(q1, "2026-06-01") == "2026-06-01"

    # Case 2: No numbers or temporal words in query, but LLM extracts a date -> nullify (hallucination)
    q2 = "أريد إجازة سنوية"
    assert adapter._validate_temporal_entity(q2, "2023-05-01") is None

    # Case 3: Query has relative temporal word -> preserve
    q3 = "أريد إجازة من غداً"
    assert adapter._validate_temporal_entity(q3, "2026-06-05") == "2026-06-05"

    # Case 4: Query contains digits but not the full date string -> preserve (since user typed digits)
    q4 = "إجازة لمدة 5 أيام"
    assert adapter._validate_temporal_entity(q4, "2026-06-10") == "2026-06-10"

@pytest.mark.asyncio
async def test_hybrid_nlp_bypass_llm_on_pending_action():
    # If has_pending_action is True, HybridNLPPipeline must NOT call LLMNLPAdapter.
    # We will pass a mock LLM client that raises an error if queried.
    mock_llm = AsyncMock()
    mock_llm.query_llm.side_effect = Exception("LLM should not be called!")
    
    pipeline = HybridNLPPipeline(mock_llm)
    
    # Query with has_pending_action=True
    intent, confidence, entities = await pipeline.analyze_query(
        query="أريد إجازة سنوية",
        has_pending_action=True
    )
    
    # It should succeed using rule-based parsing only, without raising "LLM should not be called!"
    assert intent == "SAP"
    assert entities["leave_type"] == "ANNUAL_LEAVE"

def test_rule_nlp_date_normalization():
    from services.orchestrator_service.infrastructure.nlp.rule_nlp import RuleNLPAdapter
    adapter = RuleNLPAdapter()

    # Case 1: single-digit month and day (YYYY-M-D) -> normalized to YYYY-MM-DD
    _, _, entities1 = adapter.analyze_query("2026-6-5")
    assert entities1["start_date"] == "2026-06-05"

    # Case 2: slash delimiter with single-digit month and day (D/M/YYYY) -> normalized to YYYY-MM-DD
    _, _, entities2 = adapter.analyze_query("أريد إجازة من 5/6/2026 إلى 15/6/2026")
    assert entities2["start_date"] == "2026-06-05"
    assert entities2["end_date"] == "2026-06-15"

    # Case 3: standard format -> remains standard
    _, _, entities3 = adapter.analyze_query("2026-06-05")
    assert entities3["start_date"] == "2026-06-05"

@pytest.mark.asyncio
async def test_llm_client_fallback_json():
    from services.orchestrator_service.infrastructure.llm_clients.openai_client import OpenAICompatibleLLMClient
    import json
    
    client = OpenAICompatibleLLMClient()
    messages = [
        {"role": "system", "content": "You are an expert NLP parser for a Corporate HR system."},
        {"role": "user", "content": "Query: أريد إجازة سنوية"}
    ]
    reply = client._fallback_reply(messages[-1]["content"], is_nlp_parser=True)
    
    # Verify that it returns a valid JSON that can be parsed
    parsed = json.loads(reply)
    assert parsed["intent"] == "RAG"
    assert parsed["entities"]["leave_type"] is None


