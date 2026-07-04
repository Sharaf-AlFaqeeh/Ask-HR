import os
import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
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
    action_payload: Optional[Dict[str, Any]] = None # Holds the structured UI widget for frontend

class ExecuteActionRequest(BaseModel):
    session_id: str
    action_id: str

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
        execution_details=result["execution_details"],
        action_payload=result.get("action_payload")
    )

@router.get("/chats")
def get_user_chats(principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)):
    """
    Retrieves all past chat sessions for the authenticated employee.
    """
    container = get_container()
    store = container.session_store
    
    if not principal.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="الرقم الوظيفي للموظف غير موجود في رمز الوصول."
        )
        
    if hasattr(store, "get_user_sessions"):
        sessions = store.get_user_sessions(principal.employee_id)
        result = []
        for s in sessions:
            preview = "محادثة جديدة"
            if s.history:
                # Find last user message as preview
                user_msgs = [m for m in s.history if m.role == "user"]
                if user_msgs:
                    preview = user_msgs[-1].content[:60]
                else:
                    preview = s.history[-1].content[:60]
            result.append({
                "session_id": s.session_id,
                "updated_at": s.updated_at,
                "preview": preview
            })
        return result
    return []

@router.get("/chats/{session_id}")
def get_chat_session(session_id: str, principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)):
    """
    Retrieves the full message history for a specific chat session.
    """
    container = get_container()
    store = container.session_store
    
    if not principal.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="الرقم الوظيفي للموظف غير موجود في رمز الوصول."
        )
        
    session = store.get_session(session_id)
    if session.employee_id and session.employee_id.upper() != principal.employee_id.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="لا تملك صلاحية عرض هذه الجلسة."
        )
        
    return {
        "session_id": session.session_id,
        "employee_id": session.employee_id,
        "pending_action": session.pending_action.model_dump() if session.pending_action else None,
        "history": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in session.history
        ]
    }

@router.delete("/chats/{session_id}")
def delete_user_chat(session_id: str, principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)):
    """
    Deletes a specific chat session after confirming ownership.
    """
    container = get_container()
    store = container.session_store
    
    if not principal.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="الرقم الوظيفي للموظف غير موجود في رمز الوصول."
        )
        
    session = store.get_session(session_id)
    if session.employee_id and session.employee_id.upper() != principal.employee_id.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="لا تملك صلاحية حذف هذه الجلسة."
        )
        
    deleted = store.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="لم يتم العثور على الجلسة لحذفها."
        )
    return {"success": True, "message": "تم حذف الجلسة بنجاح."}

@router.post("/chats/execute-action")
def execute_action(
    request: ExecuteActionRequest,
    principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)
):
    """
    Callback endpoint to execute a TRANSACTIONAL action once the user
    clicks the 'Submit' button in the chat interface.
    """
    container = get_container()
    store = container.session_store
    
    if not principal.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="الرقم الوظيفي للموظف غير موجود في رمز الوصول."
        )
        
    session = store.get_session(request.session_id)
    if session.employee_id and session.employee_id.upper() != principal.employee_id.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="تأكيد غير صالح: هذه الجلسة لا تنتمي لك."
        )
        
    if not session.pending_action or session.pending_action.action_name != request.action_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="لا يوجد إجراء معلق بانتظار التأكيد حالياً."
        )
        
    # Lookup Action in ActionRegistry
    from services.orchestrator_service.actions.registry import get_action_registry
    registry = get_action_registry()
    action = registry.get(request.action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="الإجراء المطلوب غير مسجل في النظام."
        )
        
    try:
        logger.info(f"Executing pending action '{request.action_id}' for employee: {principal.employee_id}")
        exec_res = action.execute(principal.employee_id, session.pending_action.parameters)
        
        # Build success confirmation message
        if request.action_id == "request_leave":
            leave_translations = {
                "ANNUAL_LEAVE": "إجازة سنوية",
                "SICK_LEAVE": "إجازة مرضية",
                "MATERNITY_LEAVE": "إجازة أمومة",
                "PATERNITY_LEAVE": "إجازة أبوة",
                "UNPAID_LEAVE": "إجازة بدون راتب"
            }
            raw_type = session.pending_action.parameters.get("leave_type", "")
            leave_desc = leave_translations.get(raw_type.upper(), raw_type)
            
            response_msg = (
                f"✅ **تم تقديم طلب الإجازة بنجاح في نظام SAP SuccessFactors!**\n\n"
                f"- **رقم الطلب:** `{exec_res.get('request_id', 'N/A')}`\n"
                f"- **نوع الإجازة:** {leave_desc}\n"
                f"- **الفترة:** من {session.pending_action.parameters.get('start_date')} إلى {session.pending_action.parameters.get('end_date')}\n"
                f"- **حالة الطلب:** بانتظار موافقة مديرك المباشر ⏳\n\n"
                f"سوف تتلقى إشعاراً بمجرد تحديث حالة الطلب. شكراً لك! 😊"
            )
        else:
            response_msg = f"✅ تم تنفيذ الإجراء '{action.name_ar}' بنجاح في نظام SAP SuccessFactors."
            
        # Add assistant message and reset pending state
        session.pending_action = None
        session.add_message(role="assistant", content=response_msg)
        store.save_session(session)
        
        return {
            "success": True,
            "response": response_msg,
            "execution_details": exec_res
        }
    except Exception as e:
        logger.error(f"Error executing action {request.action_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"حدث خطأ أثناء التنفيذ في SAP: {str(e)}"
        )

