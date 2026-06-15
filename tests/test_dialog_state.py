import pytest
from services.orchestrator_service.domain.models import SessionState
from services.orchestrator_service.application.session_manager import SessionManager

def test_session_manager_redirect_on_missing_slots():
    manager = SessionManager()
    session = SessionState(session_id="test_session_1", tenant_id="HSAGroup")
    
    # Case 1: User requests leave but missing fields exist
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
    assert "حالياً لا يمكنني تنفيذ هذا الإجراء من خلال النظام" in prompt
    assert params is None
    # Pending action should be cleared automatically to prevent getting stuck
    assert session.pending_action is None

def test_session_manager_immediate_resolution_all_slots():
    manager = SessionManager()
    session = SessionState(session_id="test_session_2", tenant_id="HSAGroup")
    
    # Case 2: User supplies all fields in a single turn
    intent = "SAP"
    entities = {
        "employee_id": "EMP102",
        "leave_type": "ANNUAL_LEAVE",
        "start_date": "2026-06-01",
        "end_date": "2026-06-10",
        "month": None
    }
    
    prompt, params = manager.process_dialog_turn(session, intent, entities)
    assert prompt is None
    assert params is not None
    assert params["employee_id"] == "EMP102"
    assert params["leave_type"] == "ANNUAL_LEAVE"
    assert params["start_date"] == "2026-06-01"
    assert params["end_date"] == "2026-06-10"
    assert session.pending_action is None

