import pytest
from unittest.mock import MagicMock, patch
from services.orchestrator_service.infrastructure.rag.qdrant_retriever import QdrantRetrieverAdapter

class MockQdrantResult:
    def __init__(self, document: str, metadata: dict):
        self.document = document
        self.metadata = metadata

@pytest.mark.asyncio
@patch("services.orchestrator_service.infrastructure.rag.qdrant_retriever.get_tenant_id")
@patch("qdrant_client.QdrantClient")
async def test_qdrant_retriever_tenant_equivalence(mock_qdrant_client_cls, mock_get_tenant_id):
    # 1. تهيئة الـ Mocks
    mock_client = MagicMock()
    mock_qdrant_client_cls.return_value = mock_client
    
    # محاكاة وجود المجموعات
    mock_collection = MagicMock()
    mock_collection.name = "hr_policies"
    mock_client.get_collections.return_value = MagicMock(collections=[mock_collection])
    
    # 2. إنشاء بيانات اختبارية لـ Qdrant تحتوي على معرّفات مستأجرين مختلفة
    mock_results = [
        MockQdrantResult(
            document="سياسة الإجازات الخاصة بـ HSA_Group",
            metadata={"tenant_id": "HSA_Group", "source": "HSA_Group_Policy.pdf"}
        ),
        MockQdrantResult(
            document="سياسة البدلات الخاصة بـ HSAGroup",
            metadata={"tenant_id": "HSAGroup", "source": "HSAGroup_Policy.pdf"}
        ),
        MockQdrantResult(
            document="سياسة سرية للمستأجر الخارجي",
            metadata={"tenant_id": "OtherCompany", "source": "Other_Policy.pdf"}
        )
    ]
    mock_client.query.return_value = mock_results
    
    # 3. سيناريو 1: المستأجر النشط هو "HSAGroup"
    mock_get_tenant_id.return_value = "HSAGroup"
    
    # تفعيل Adapter
    adapter = QdrantRetrieverAdapter()
    context = adapter.retrieve_context("شروط الإجازات", limit=3)
    
    # يجب أن يسترجع سياسات HSA_Group و HSAGroup، ويستبعد OtherCompany
    assert "HSA_Group" in context
    assert "HSAGroup" in context
    assert "OtherCompany" not in context

    # 4. سيناريو 2: المستأجر النشط هو "HSA_Group"
    mock_get_tenant_id.return_value = "HSA_Group"
    context = adapter.retrieve_context("شروط الإجازات", limit=3)
    
    # يجب أيضاً أن يسترجع سياسات HSA_Group و HSAGroup، ويستبعد OtherCompany
    assert "HSA_Group" in context
    assert "HSAGroup" in context
    assert "OtherCompany" not in context
