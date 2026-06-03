import time
from typing import Dict, Tuple
from services.orchestrator_service.domain.interfaces import ISessionStore
from services.orchestrator_service.domain.models import SessionState
from core.logger import get_logger

logger = get_logger("in_memory_session_store")

class InMemorySessionStore(ISessionStore):
    """
    Adapter implementing the ISessionStore port.
    Stores session states in memory. Perfect for development and single-instance deployments.
    Can be easily swapped with a RedisSessionStore in production.
    """
    def __init__(self):
        # Dict mapping (tenant_id, session_id) -> SessionState
        self._sessions: Dict[Tuple[str, str], SessionState] = {}
        logger.info("InMemorySessionStore adapter initialized")

    def get_session(self, session_id: str, tenant_id: str = "default_tenant") -> SessionState:
        key = (tenant_id, session_id)
        if key not in self._sessions:
            logger.info(f"Creating new session state object: {session_id} for tenant: {tenant_id}")
            self._sessions[key] = SessionState(session_id=session_id, tenant_id=tenant_id)
        else:
            logger.info(f"Retrieved existing session state: {session_id} (Tenant: {tenant_id})")
        return self._sessions[key]

    def save_session(self, session: SessionState) -> None:
        key = (session.tenant_id, session.session_id)
        session.updated_at = time.time()
        self._sessions[key] = session
        logger.info(f"Saved session state: {session.session_id} (Tenant: {session.tenant_id})")

    def delete_session(self, session_id: str) -> bool:
        # Scan and delete the session matching session_id across any tenants
        keys_to_delete = [k for k in self._sessions.keys() if k[1] == session_id]
        if not keys_to_delete:
            return False
        for key in keys_to_delete:
            del self._sessions[key]
            logger.info(f"Deleted session state: {key[1]} (Tenant: {key[0]})")
        return True
