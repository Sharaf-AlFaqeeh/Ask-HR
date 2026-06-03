import time
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str # 'user', 'assistant', 'system'
    content: str
    timestamp: float = Field(default_factory=time.time)

class PendingAction(BaseModel):
    action_name: str # 'request_leave' | 'get_salary_slip' | 'get_profile'
    parameters: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[str] = Field(default_factory=list)

class SessionState(BaseModel):
    session_id: str
    tenant_id: str = "default_tenant"
    employee_id: Optional[str] = None
    history: List[Message] = Field(default_factory=list)
    pending_action: Optional[PendingAction] = None
    updated_at: float = Field(default_factory=time.time)

    def add_message(self, role: str, content: str) -> None:
        self.history.append(Message(role=role, content=content))
        self.updated_at = time.time()

    def clear_history(self) -> None:
        self.history.clear()
        self.pending_action = None
        self.updated_at = time.time()

# Domain output data structures
class EmployeeProfile(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    department: str
    position: str
    email: str
    status: str

class LeaveRequestResponse(BaseModel):
    request_id: str
    employee_id: str
    leave_type: str
    start_date: str
    end_date: str
    status: str
    message: str

class SalarySlipResponse(BaseModel):
    employee_id: str
    month: str
    basic_salary: float
    housing_allowance: float
    transport_allowance: float
    deductions: float
    net_salary: float
