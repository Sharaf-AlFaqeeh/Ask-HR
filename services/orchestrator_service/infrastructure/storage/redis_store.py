import json
import time
from typing import Optional, List
import redis
from services.orchestrator_service.domain.interfaces import ISessionStore
from services.orchestrator_service.domain.models import SessionState
from core.logger import get_logger

logger = get_logger("redis_session_store")

class RedisSessionStore(ISessionStore):
    """
    High-performance Redis adapter implementing the ISessionStore port.
    Supports session TTL, multi-user concurrency, and horizontal scalability.
    """
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ttl: int = 2592000 # 30 days default in seconds
    ):
        self.ttl = ttl
        logger.info(f"Initializing RedisSessionStore with host={host}:{port}, db={db}, ttl={ttl}s")
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            socket_connect_timeout=5,
            socket_timeout=5
        )

    def get_session(self, session_id: str, tenant_id: str = "default_tenant") -> SessionState:
        session_key = f"askhr:session:{session_id}"
        try:
            data = self.redis.get(session_key)
            if not data:
                # Return a new unsaved session state object
                logger.debug(f"Session {session_id} not found in Redis, returning new state")
                return SessionState(session_id=session_id, tenant_id=tenant_id)
                
            val = data.decode("utf-8") if isinstance(data, bytes) else data
            return SessionState.model_validate_json(val)
        except Exception as e:
            logger.error(f"Error fetching session {session_id} from Redis: {e}", exc_info=True)
            # Fail-safe: return new session state to keep application running
            return SessionState(session_id=session_id, tenant_id=tenant_id)

    def save_session(self, session: SessionState) -> None:
        session.updated_at = time.time()
        session_key = f"askhr:session:{session.session_id}"
        try:
            session_json = session.model_dump_json()
            # Save session data with TTL
            self.redis.set(session_key, session_json, ex=self.ttl)
            
            # If user identity is attached to session, add to their session index
            if session.employee_id:
                user_key = f"askhr:user:{session.tenant_id}:{session.employee_id.upper()}:sessions"
                # zadd takes a dict mapping member -> score
                self.redis.zadd(user_key, {session.session_id: session.updated_at})
                # Refresh user set expiry
                self.redis.expire(user_key, self.ttl)
                
            logger.info(f"Successfully saved session {session.session_id} to Redis")
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id} to Redis: {e}", exc_info=True)

    def delete_session(self, session_id: str) -> bool:
        session_key = f"askhr:session:{session_id}"
        try:
            # Fetch session first to clean up user session sorted set
            data = self.redis.get(session_key)
            if not data:
                return False
                
            try:
                val = data.decode("utf-8") if isinstance(data, bytes) else data
                session = SessionState.model_validate_json(val)
                if session.employee_id:
                    user_key = f"askhr:user:{session.tenant_id}:{session.employee_id.upper()}:sessions"
                    self.redis.zrem(user_key, session_id)
            except Exception as e:
                logger.error(f"Error cleaning up user index for session {session_id}: {e}")

            deleted = self.redis.delete(session_key)
            if deleted:
                logger.info(f"Deleted session {session_id} from Redis")
            return bool(deleted)
        except Exception as e:
            logger.error(f"Failed to delete session {session_id} from Redis: {e}", exc_info=True)
            return False

    def get_user_sessions(self, employee_id: str, tenant_id: str = "HSAGroup") -> List[SessionState]:
        user_key = f"askhr:user:{tenant_id}:{employee_id.upper()}:sessions"
        try:
            # Retrieve all session IDs ordered by updated_at descending (newest first)
            session_ids_bytes = self.redis.zrevrange(user_key, 0, -1)
            if not session_ids_bytes:
                return []
                
            session_ids = [
                sid.decode("utf-8") if isinstance(sid, bytes) else sid 
                for sid in session_ids_bytes
            ]
            
            sessions = []
            dead_session_ids = []
            
            # pipeline for batch fetching session data
            pipe = self.redis.pipeline()
            for sid in session_ids:
                pipe.get(f"askhr:session:{sid}")
            results = pipe.execute()
            
            for sid, data in zip(session_ids, results):
                if data:
                    try:
                        val = data.decode("utf-8") if isinstance(data, bytes) else data
                        sessions.append(SessionState.model_validate_json(val))
                    except Exception as e:
                        logger.error(f"Error deserializing user session {sid}: {e}")
                        dead_session_ids.append(sid)
                else:
                    # Key has expired from Redis due to TTL
                    dead_session_ids.append(sid)
                    
            # Clean up references to dead/expired sessions
            if dead_session_ids:
                try:
                    self.redis.zrem(user_key, *dead_session_ids)
                    logger.info(f"Pruned {len(dead_session_ids)} expired session references for user {employee_id}")
                except Exception as e:
                    logger.error(f"Error pruning dead session references: {e}")
                    
            return sessions
        except Exception as e:
            logger.error(f"Failed to fetch sessions for user {employee_id} from Redis: {e}", exc_info=True)
            return []
