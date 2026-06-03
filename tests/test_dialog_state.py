import pytest
from services.orchestrator_service.domain.models import SessionState
from services.orchestrator_service.application.session_manager import SessionManager

def test_session_manager_multi_turn_slot_filling():
    manager = SessionManager()
    session = SessionState(session_id="test_session_1", tenant_id="HSAGroup")
    
    # Turn 1: User requests leave but doesn't supply employee ID or dates
    intent = "SAP"
    entities = {
        "employee_id": None,
        "leave_type": "ANNUAL_LEAVE",
        "start_date": None,
        "end_date": None,
        "month": None
    }
    
    prompt, params = manager.process_dialog_turn(session, intent, entities)
    assert prompt is not None
    assert "الرقم الوظيفي" in prompt
    assert params is None
    assert session.pending_action is not None
    assert session.pending_action.action_name == "request_leave"
    assert session.pending_action.parameters["leave_type"] == "ANNUAL_LEAVE"
    
    # Turn 2: User responds with employee ID
    entities = {
        "employee_id": "EMP102",
        "leave_type": None,
        "start_date": None,
        "end_date": None,
        "month": None
    }
    
    prompt, params = manager.process_dialog_turn(session, intent, entities)
    assert prompt is not None
    assert "تاريخ بدء الإجازة" in prompt
    assert params is None
    assert session.employee_id == "EMP102"
    assert session.pending_action.parameters["employee_id"] == "EMP102"
    
    # Turn 3: User responds with dates
    entities = {
        "employee_id": None,
        "leave_type": None,
        "start_date": "2026-06-01",
        "end_date": "2026-06-10",
        "month": None
    }
    
    prompt, params = manager.process_dialog_turn(session, intent, entities)
    assert prompt is None # No prompt because it's fully complete
    assert params is not None
    assert params["employee_id"] == "EMP102"
    assert params["leave_type"] == "ANNUAL_LEAVE"
    assert params["start_date"] == "2026-06-01"
    assert params["end_date"] == "2026-06-10"
    
    # Verify that pending action is cleared
    assert session.pending_action is None
