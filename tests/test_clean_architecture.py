import pytest
from services.orchestrator_service.application.flow_orchestrator import FlowOrchestrator
from services.orchestrator_service.infrastructure.nlp.hybrid_nlp import HybridNLPPipeline

@pytest.mark.asyncio
async def test_flow_orchestrator_rag_retrieval(mock_llm, mock_retriever, mock_hr, session_store):
    # Initialize a pipeline with mock LLM
    nlp_pipeline = HybridNLPPipeline(mock_llm)
    
    orchestrator = FlowOrchestrator(
        llm_client=mock_llm,
        retriever=mock_retriever,
        hr_client=mock_hr,
        session_store=session_store,
        nlp_pipeline=nlp_pipeline
    )
    
    result = await orchestrator.handle_message(
        session_id="test_sess_rag",
        tenant_id="HSAGroup",
        query="ما هي سياسة الإجازة السنوية؟"
    )
    
    assert result["intent"] == "RAG"
    assert result["context_used"] is True
    assert "الإجازة" in result["response"] or "المساعد الذكي" in result["response"]

@pytest.mark.asyncio
async def test_flow_orchestrator_sap_leave_workflow(mock_llm, mock_retriever, mock_hr, session_store):
    nlp_pipeline = HybridNLPPipeline(mock_llm)
    
    orchestrator = FlowOrchestrator(
        llm_client=mock_llm,
        retriever=mock_retriever,
        hr_client=mock_hr,
        session_store=session_store,
        nlp_pipeline=nlp_pipeline
    )
    
    # Send complete message to bypass multi-turn slots
    result = await orchestrator.handle_message(
        session_id="test_sess_sap",
        tenant_id="HSAGroup",
        query="أريد تقديم إجازة سنوية للموظف emp102 من 2026-06-01 إلى 2026-06-10"
    )
    
    assert result["intent"] == "SAP"
    assert result["sap_executed"] is False
    assert result["action_payload"] is not None
    assert result["action_payload"]["action_id"] == "request_leave"

