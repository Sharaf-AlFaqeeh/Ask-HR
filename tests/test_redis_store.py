import sys
import os
from unittest.mock import MagicMock, patch
import pytest

# Adjust paths to import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.orchestrator_service.infrastructure.storage.redis_store import RedisSessionStore
from services.orchestrator_service.domain.models import SessionState

@patch("redis.Redis")
def test_redis_store_save_and_get(mock_redis_class):
    mock_redis = MagicMock()
    mock_redis_class.return_value = mock_redis
    
    # Setup store
    store = RedisSessionStore(host="localhost", port=6379, db=0, ttl=3600)
    
    # Mock redis get/set
    stored_data = {}
    def mock_set(key, val, ex=None):
        stored_data[key] = val
        return True
        
    def mock_get(key):
        return stored_data.get(key)
        
    mock_redis.set.side_effect = mock_set
    mock_redis.get.side_effect = mock_get
    
    # Save a session
    session = SessionState(session_id="session_123", tenant_id="HSAGroup", employee_id="EMP999")
    session.add_message("user", "Hello")
    session.add_message("assistant", "Hi there")
    
    store.save_session(session)
    
    # Assert set was called correctly
    mock_redis.set.assert_called_once()
    assert "session_123" in mock_redis.set.call_args[0][0]
    
    # Assert zadd was called for employee mapping
    mock_redis.zadd.assert_called_once_with(
        "askhr:user:HSAGroup:EMP999:sessions",
        {"session_123": session.updated_at}
    )
    
    # Fetch session
    loaded = store.get_session("session_123", "HSAGroup")
    assert loaded is not None
    assert loaded.session_id == "session_123"
    assert loaded.employee_id == "EMP999"
    assert len(loaded.history) == 2
    assert loaded.history[0].content == "Hello"
    assert loaded.history[1].role == "assistant"

@patch("redis.Redis")
def test_redis_store_delete(mock_redis_class):
    mock_redis = MagicMock()
    mock_redis_class.return_value = mock_redis
    
    store = RedisSessionStore(host="localhost", port=6379, db=0, ttl=3600)
    
    # Mock session data exists in Redis
    session = SessionState(session_id="session_123", tenant_id="HSAGroup", employee_id="EMP999")
    session_json = session.model_dump_json()
    
    mock_redis.get.return_value = session_json.encode()
    mock_redis.delete.return_value = 1
    
    deleted = store.delete_session("session_123")
    assert deleted is True
    mock_redis.delete.assert_called_once_with("askhr:session:session_123")
    mock_redis.zrem.assert_called_once_with("askhr:user:HSAGroup:EMP999:sessions", "session_123")

@patch("redis.Redis")
def test_redis_get_user_sessions_with_cleanup(mock_redis_class):
    mock_redis = MagicMock()
    mock_redis_class.return_value = mock_redis
    
    store = RedisSessionStore(host="localhost", port=6379, db=0, ttl=3600)
    
    # Mock zrevrange returning two session IDs (one alive, one expired/dead)
    mock_redis.zrevrange.return_value = [b"sess_alive", b"sess_dead"]
    
    # Mock pipeline execution
    # pipeline returns [data_alive, None]
    mock_pipeline = MagicMock()
    mock_redis.pipeline.return_value = mock_pipeline
    
    session_alive = SessionState(session_id="sess_alive", tenant_id="HSAGroup", employee_id="EMP999")
    session_alive_json = session_alive.model_dump_json()
    
    mock_pipeline.execute.return_value = [session_alive_json.encode(), None]
    
    user_sessions = store.get_user_sessions("EMP999", "HSAGroup")
    
    # Verify we got only the alive session
    assert len(user_sessions) == 1
    assert user_sessions[0].session_id == "sess_alive"
    
    # Verify expired session was pruned from the user's sessions index
    mock_redis.zrem.assert_called_once_with("askhr:user:HSAGroup:EMP999:sessions", "sess_dead")

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__]))
