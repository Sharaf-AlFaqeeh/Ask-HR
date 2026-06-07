from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from services.orchestrator_service.domain.models import (
    SessionState, EmployeeProfile, LeaveRequestResponse, SalarySlipResponse
)

class ILLMClient(ABC):
    @abstractmethod
    async def query_llm(self, messages: List[Dict[str, str]], temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        """Sends messages to the LLM and retrieves the response."""
        pass

class IRetriever(ABC):
    @abstractmethod
    def retrieve_context(self, query: str, limit: int = 3) -> str:
        """Retrieves text context relevant to the query from Vector DB."""
        pass

class IHRSystemClient(ABC):
    @abstractmethod
    def get_employee_profile(self, employee_id: str) -> EmployeeProfile:
        """Retrieves employee profile from SAP SuccessFactors."""
        pass

    @abstractmethod
    def request_leave(self, employee_id: str, leave_type: str, start_date: str, end_date: str) -> LeaveRequestResponse:
        """Submits a leave request to SAP SuccessFactors."""
        pass

    @abstractmethod
    def get_salary_slip(self, employee_id: str, month: str) -> SalarySlipResponse:
        """Retrieves salary slip details from SAP SuccessFactors Payroll."""
        pass

class ISessionStore(ABC):
    @abstractmethod
    def get_session(self, session_id: str, tenant_id: str = "default_tenant") -> SessionState:
        """Gets or creates a session by ID."""
        pass

    @abstractmethod
    def save_session(self, session: SessionState) -> None:
        """Saves session state changes to storage."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Deletes a session from storage."""
        pass

class INLPPipeline(ABC):
    @abstractmethod
    async def analyze_query(self, query: str, has_pending_action: bool = False) -> Tuple[str, float, Dict[str, Any]]:
        """
        Analyzes query to extract intent, confidence, and entities.
        Returns: Tuple[intent_name, confidence_score, extracted_entities_dict]
        """
        pass
