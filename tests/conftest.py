import os
import sys
from typing import List, Dict, Any, Tuple, Optional, AsyncGenerator
import pytest

# Add root folder to sys.path to resolve core and services imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.orchestrator_service.domain.interfaces import ILLMClient, IRetriever, IHRSystemClient
from services.orchestrator_service.domain.models import EmployeeProfile, LeaveRequestResponse, SalarySlipResponse
from services.orchestrator_service.infrastructure.storage.in_memory import InMemorySessionStore

class MockLLMClient(ILLMClient):
    async def query_llm(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        # Simple rule-based mock model responder for testing
        user_msg = messages[-1]["content"].lower()
        if "leave" in user_msg or "إجازة" in user_msg:
            return "تمت معالجة الإجازة بنجاح في المحاكاة."
        elif "salary" in user_msg or "راتب" in user_msg:
            return "تفاصيل الراتب هي: الأساسي 4000، الصافي 4700 دولارات."
        return "مرحباً! أنا المساعد الذكي لمجموعة HSA."

    async def query_llm_stream(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> AsyncGenerator[str, None]:
        response = await self.query_llm(messages, temperature, max_tokens)
        # Yield the response in chunks for streaming
        for word in response.split(" "):
            yield word + " "


class MockRetriever(IRetriever):
    def retrieve_context(self, query: str, limit: int = 3) -> str:
        return "[مصدر: اختبار] يحق للموظف إجازة سنوية قدرها 30 يوماً."

    def retrieve_context_with_metadata(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        return [{
            "source": "HR_Policy_Test.pdf",
            "category": "TestCategory",
            "page_number": 2,
            "text": "يحق للموظف إجازة سنوية قدرها 30 يوماً."
        }]

class MockHRSystemClient(IHRSystemClient):
    def get_employee_profile(self, employee_id: str) -> EmployeeProfile:
        return EmployeeProfile(
            employee_id=employee_id,
            first_name="Test",
            last_name="User",
            department="QA",
            position="Engineer",
            email="test.user@hsagroup.com",
            status="Active"
        )

    def request_leave(self, employee_id: str, leave_type: str, start_date: str, end_date: str) -> LeaveRequestResponse:
        return LeaveRequestResponse(
            request_id="LR-TEST123",
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            status="APPROVED",
            message="Mock approved leave."
        )

    def get_salary_slip(self, employee_id: str, month: str) -> SalarySlipResponse:
        return SalarySlipResponse(
            employee_id=employee_id,
            month=month,
            basic_salary=3000.0,
            housing_allowance=750.0,
            transport_allowance=300.0,
            deductions=150.0,
            net_salary=3900.0
        )

@pytest.fixture
def mock_llm():
    return MockLLMClient()

@pytest.fixture
def mock_retriever():
    return MockRetriever()

@pytest.fixture
def mock_hr():
    return MockHRSystemClient()

@pytest.fixture
def session_store():
    return InMemorySessionStore()
