import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

# Adjust paths to import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.orchestrator_service.infrastructure.llm_clients.openai_client import OpenAICompatibleLLMClient
from services.orchestrator_service.application.flow_orchestrator import FlowOrchestrator
from services.orchestrator_service.domain.models import SessionState, Message
from services.orchestrator_service.infrastructure.storage.in_memory import InMemorySessionStore

@pytest.mark.asyncio
async def test_openai_client_streaming_fallback():
    # If connection fails, it should use the fallback mechanism and yield mock completion response
    client = OpenAICompatibleLLMClient()
    
    # We patch the api request to raise exception to trigger fallback
    with patch.object(client.client, "stream", side_effect=Exception("Connection refused")):
        chunks = []
        async for chunk in client.query_llm_stream([{"role": "user", "content": "ما هي سياسة الإجازة؟"}]):
            chunks.append(chunk)
            
        full_text = "".join(chunks)
        assert "خادم الاستدلال غير متوفر" in full_text
        assert len(chunks) > 1

@pytest.mark.asyncio
async def test_flow_orchestrator_handle_message_stream():
    # Mock dependencies
    mock_llm = MagicMock()
    mock_retriever = MagicMock()
    mock_hr = MagicMock()
    session_store = InMemorySessionStore()
    mock_nlp = AsyncMock()
    
    # Configure mock NLP pipeline
    # Intent: RAG, entities: empty
    mock_nlp.analyze_query.return_value = ("RAG", 1.0, {})
    
    # Configure mock LLM stream
    async def mock_query_llm_stream(messages, temperature=None, max_tokens=None):
        yield "الرد "
        yield "المقترح "
        yield "من "
        yield "الذكاء "
        yield "الاصطناعي."
    
    mock_llm.query_llm_stream.side_effect = mock_query_llm_stream
    
    # Mock retriever context
    mock_retriever.retrieve_context_with_metadata.return_value = [{
        "source": "HR_Policy.pdf",
        "category": "Leaves",
        "page_number": 1,
        "text": "تفاصيل السياسة..."
    }]
    
    orchestrator = FlowOrchestrator(
        llm_client=mock_llm,
        retriever=mock_retriever,
        hr_client=mock_hr,
        session_store=session_store,
        nlp_pipeline=mock_nlp
    )
    
    # Run streaming handler
    results = []
    async for chunk in orchestrator.handle_message_stream(
        session_id="stream_session_1",
        tenant_id="HSAGroup",
        query="مرحبا"
    ):
        results.append(chunk)
        
    # Check that chunks were yielded
    # Chunks are:
    # 1. is_thinking chunk containing citations
    # 2-6. 5 text token chunks
    # 7. final non-chunk packet
    assert len(results) == 7 # 1 thinking + 5 tokens + 1 final complete payload
    
    # Check thinking chunk
    assert results[0]["is_thinking"] is True
    assert results[0]["is_chunk"] is True
    assert len(results[0]["execution_details"]["citations"]) == 1
    
    # Check text chunks
    for i in range(1, 6):
        assert results[i]["is_chunk"] is True
        
    assert results[6]["is_chunk"] is False
    assert results[6]["response"] == "الرد المقترح من الذكاء الاصطناعي."
    assert results[6]["intent"] == "RAG"
    assert results[6]["context_used"] is True
    assert len(results[6]["execution_details"]["citations"]) == 1
    
    # Check session was saved in store
    saved_session = session_store.get_session("stream_session_1", "HSAGroup")
    assert saved_session is not None
    assert len(saved_session.history) == 2
    assert saved_session.history[1].role == "assistant"
    assert saved_session.history[1].content == "الرد المقترح من الذكاء الاصطناعي."

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__]))
