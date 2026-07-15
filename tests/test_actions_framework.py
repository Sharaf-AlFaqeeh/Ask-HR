import sys
import os
import shutil

# Adjust paths to import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.security.sharepoint_mock import authenticate_sharepoint, get_user_by_employee_id
from core.security.auth import create_access_token, verify_jwt_or_bearer_token, UserPrincipal
from services.orchestrator_service.actions.registry import get_action_registry
from services.orchestrator_service.infrastructure.storage.sqlite_store import SQLiteSessionStore
from services.orchestrator_service.domain.models import SessionState, Message

def test_mock_sharepoint_auth():
    print("Running Test: Mock SharePoint Auth...")
    # Test valid login
    user = authenticate_sharepoint("sharaf@hsagroup.com", "password123")
    assert user is not None, "Failed authenticating valid email"
    assert user["employee_id"] == "EMP101", f"Expected EMP101, got {user['employee_id']}"
    
    # Test valid username lookup
    user_by_username = authenticate_sharepoint("sharaf", "password123")
    assert user_by_username is not None, "Failed authenticating valid username"
    assert user_by_username["employee_id"] == "EMP101"
    
    # Test invalid password
    user_invalid = authenticate_sharepoint("sharaf", "wrong_password")
    assert user_invalid is None, "Logged in with wrong password!"
    print("✅ SharePoint Auth tests passed.")

def test_jwt_generation_and_verification():
    print("Running Test: JWT Generation & Verification...")
    claims = {
        "sub": "EMP102",
        "employee_id": "EMP102",
        "tenant_id": "HSAGroup",
        "roles": ["employee", "manager"],
        "scopes": ["read:profile"]
    }
    
    token = create_access_token(claims)
    assert isinstance(token, str), "Token must be a string"
    
    # Verify using verify_jwt_or_bearer_token
    auth_header = f"Bearer {token}"
    principal = verify_jwt_or_bearer_token(auth_header)
    assert principal is not None, "Failed verifying generated token"
    assert principal.employee_id == "EMP102"
    assert principal.tenant_id == "HSAGroup"
    assert "manager" in principal.roles
    print("✅ JWT Generation & Verification tests passed.")

def test_sqlite_persistence():
    print("Running Test: SQLite Persistence...")
    # Create a temporary test database file
    db_file = "test_askhr_sessions.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    store = SQLiteSessionStore(db_file)
    
    # Create test session
    session_id = "test_sess_999"
    session = SessionState(session_id=session_id, tenant_id="HSAGroup", employee_id="EMP102")
    session.add_message("user", "مرحباً يا مساعد")
    session.add_message("assistant", "أهلاً بك، كيف يمكنني مساعدتك؟")
    
    # Save session
    store.save_session(session)
    
    # Load and verify session
    loaded = store.get_session(session_id, "HSAGroup")
    assert loaded is not None
    assert loaded.employee_id == "EMP102"
    assert len(loaded.history) == 2
    assert loaded.history[0].content == "مرحباً يا مساعد"
    assert loaded.history[1].role == "assistant"
    
    # Test get_user_sessions
    user_sessions = store.get_user_sessions("EMP102", "HSAGroup")
    assert len(user_sessions) == 1
    assert user_sessions[0].session_id == session_id
    
    # Delete session
    deleted = store.delete_session(session_id)
    assert deleted is True, "Failed deleting session"
    
    loaded_deleted = store.get_session(session_id, "HSAGroup")
    assert len(loaded_deleted.history) == 0, "Messages were not deleted"
    
    # Cleanup test db
    if os.path.exists(db_file):
        os.remove(db_file)
    print("✅ SQLite Persistence tests passed.")

def test_action_registry_lookup():
    print("Running Test: Action Registry Lookup...")
    registry = get_action_registry()
    
    # Check leave action
    leave_action = registry.get("request_leave")
    assert leave_action is not None
    assert leave_action.action_id == "request_leave"
    assert leave_action.action_type.value == "TRANSACTIONAL"
    
    # Check validation
    valid, err = leave_action.validate({"start_date": "2026-08-01", "end_date": "2026-08-10"})
    assert valid is True
    assert err is None
    
    invalid, err = leave_action.validate({"start_date": "2026-08-10", "end_date": "2026-08-01"})
    assert invalid is False
    assert err is not None
    print(f"  Leave action validation correctly failed: {err}")
    
    # Check payslip action
    payslip_action = registry.get("get_salary_slip")
    assert payslip_action is not None
    assert payslip_action.action_type.value == "INQUIRY"
    
    ui_template = payslip_action.get_ui_template({"month": "May 2026"})
    assert "status_steps_ar" in ui_template
    print("✅ Action Registry & Actions tests passed.")

if __name__ == "__main__":
    print("=== AskHR Actions Framework & Identity Verification Tests ===")
    try:
        test_mock_sharepoint_auth()
        test_jwt_generation_and_verification()
        test_sqlite_persistence()
        test_action_registry_lookup()
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉")
    except AssertionError as e:
        print(f"\n❌ TEST FAILURE: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)
