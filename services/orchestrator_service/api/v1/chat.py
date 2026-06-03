import os
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.security.auth import verify_jwt_or_bearer_token, UserPrincipal
from services.orchestrator_service.di.container import get_container
from core.logger import get_logger

logger = get_logger("orchestrator_chat_api")
router = APIRouter(prefix="/v1")

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    employee_id: Optional[str] = None

class ChatResponse(BaseModel):
    query: str
    intent: str
    confidence: float
    entities: Dict[str, Any]
    response: str
    context_used: bool = False
    sap_executed: bool = False
    session_pending: bool = False
    session_id: str
    execution_details: Dict[str, Any]

@router.post("/chat", response_model=ChatResponse)
async def process_chat(
    request: ChatRequest, 
    principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)
):
    """
    Stateful conversational chat endpoint. Coordinates multi-turn slot filling
    for SAP SuccessFactors and policy retrievals from Qdrant Vector DB.
    """
    # 1. Resolve session ID and tenant ID
    session_id = request.session_id or str(uuid.uuid4().hex[:12])
    tenant_id = principal.tenant_id
    
    # Prioritize explicitly passed employee ID, otherwise use JWT claim's employee ID
    emp_id = request.employee_id or principal.employee_id

    logger.info(
        "Chat request received", 
        extra_fields={
            "session_id": session_id, 
            "tenant_id": tenant_id, 
            "employee_id": emp_id,
            "query": request.query
        }
    )

    # 2. Get FlowOrchestrator from DI container
    container = get_container()
    orchestrator = container.flow_orchestrator

    # 3. Handle the message flow
    result = await orchestrator.handle_message(
        session_id=session_id,
        tenant_id=tenant_id,
        query=request.query,
        override_employee_id=emp_id
    )

    # 4. Return formatted response containing session ID to allow UI continuation
    return ChatResponse(
        query=result["query"],
        intent=result["intent"],
        confidence=result["confidence"],
        entities=result["entities"],
        response=result["response"],
        context_used=result["context_used"],
        sap_executed=result["sap_executed"],
        session_pending=result["session_pending"],
        session_id=session_id,
        execution_details=result["execution_details"]
    )
