import pytest
from services.orchestrator_service.domain.models import SessionState
from services.orchestrator_service.application.session_manager import SessionManager
from core.config_manager import get_settings

def test_session_manager_redirect_on_missing_slots_production(monkeypatch):
    # Force mock_mode = False to simulate production redirect behavior
    settings = get_settings()
    monkeypatch.setattr(settings.sap, "mock_mode", False)

    manager = SessionManager()
    session = SessionState(session_id="test_session_1", tenant_id="HSAGroup")
    
    intent = "SAP"
    entities = {
        "employee_id": None,
        "leave_type": "ANNUAL_LEAVE",
        "start_date": None,
        "end_date": None,
        "month": None
    }
    
    prompt, params, form_payload = manager.process_dialog_turn(session, intent, entities)
    assert prompt is not None
    assert "حالياً لا يمكنني تنفيذ هذا الإجراء من خلال النظام" in prompt
    assert params is None
    # Pending action should be cleared automatically in production to prevent getting stuck
    assert session.pending_action is None

def test_session_manager_slot_filling_in_development(monkeypatch):
    # Force mock_mode = True to simulate development/testing slot-filling behavior
    settings = get_settings()
    monkeypatch.setattr(settings.sap, "mock_mode", True)

    manager = SessionManager()
    session = SessionState(session_id="test_session_dev", tenant_id="HSAGroup")
    
    intent = "SAP"
    entities = {
        "employee_id": None,
        "leave_type": "ANNUAL_LEAVE",
        "start_date": None,
        "end_date": None,
        "month": None
    }
    
    prompt, params, form_payload = manager.process_dialog_turn(session, intent, entities)
    # Since employee_id is also missing, we expect a text prompt for it, and the form_payload as well
    assert prompt is not None
    assert "الرقم الوظيفي" in prompt
    assert params is None
    assert form_payload is not None
    assert form_payload["form_type"] == "leave_request"
    # Pending action must remain active to continue collecting inputs
    assert session.pending_action is not None
    assert session.pending_action.action_name == "request_leave"

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
    
    prompt, params, form_payload = manager.process_dialog_turn(session, intent, entities)
    assert prompt is None
    assert params is not None
    assert form_payload is None
    assert params["employee_id"] == "EMP102"
    assert params["leave_type"] == "ANNUAL_LEAVE"
    assert params["start_date"] == "2026-06-01"
    assert params["end_date"] == "2026-06-10"
    assert session.pending_action is None
