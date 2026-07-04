import sqlite3
import json
import time
from typing import Optional, List, Tuple
from services.orchestrator_service.domain.interfaces import ISessionStore
from services.orchestrator_service.domain.models import SessionState, Message, PendingAction
from core.logger import get_logger

logger = get_logger("sqlite_session_store")

class SQLiteSessionStore(ISessionStore):
    """
    Persistent SQLite adapter implementing the ISessionStore port.
    Guarantees session history is kept across server restarts.
    """
    def __init__(self, db_path: str = "askhr_sessions.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                tenant_id TEXT,
                employee_id TEXT,
                pending_action TEXT, -- JSON string representing PendingAction
                updated_at REAL
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"SQLiteSessionStore database initialized at {self.db_path}")

    def get_session(self, session_id: str, tenant_id: str = "default_tenant") -> SessionState:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            # Return new unsaved session
            return SessionState(session_id=session_id, tenant_id=tenant_id)
            
        pending_action = None
        if row["pending_action"]:
            try:
                pa_data = json.loads(row["pending_action"])
                pending_action = PendingAction(**pa_data)
            except Exception as e:
                logger.error(f"Error parsing pending action for session {session_id}: {e}")
            
        # Fetch messages history ordered chronologically
        cursor.execute("SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
        msg_rows = cursor.fetchall()
        history = [
            Message(role=mr["role"], content=mr["content"], timestamp=mr["timestamp"])
            for mr in msg_rows
        ]
            
        conn.close()
        
        return SessionState(
            session_id=row["session_id"],
            tenant_id=row["tenant_id"],
            employee_id=row["employee_id"],
            history=history,
            pending_action=pending_action,
            updated_at=row["updated_at"]
        )

    def save_session(self, session: SessionState) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        pending_action_json = None
        if session.pending_action:
            pending_action_json = json.dumps(session.pending_action.model_dump())
            
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (session_id, tenant_id, employee_id, pending_action, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session.session_id, session.tenant_id, session.employee_id, pending_action_json, time.time()))
        
        # Sync messages: clear and re-insert history
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session.session_id,))
        for msg in session.history:
            cursor.execute("""
                INSERT INTO messages (session_id, role, content, timestamp)
                VALUES (?, ?, ?, ?)
            """, (session.session_id, msg.role, msg.content, msg.timestamp))
            
        conn.commit()
        conn.close()
        logger.info(f"Successfully saved session {session.session_id} to SQLite DB")

    def delete_session(self, session_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
        exists = cursor.fetchone() is not None
        
        if exists:
            # Cascade delete due to DB schema
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            logger.info(f"Deleted session {session_id} from SQLite DB")
            
        conn.close()
        return exists

    def get_user_sessions(self, employee_id: str, tenant_id: str = "HSAGroup") -> List[SessionState]:
        """
        Helper method to fetch all chat sessions for a specific employee.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id FROM sessions 
            WHERE employee_id = ? AND tenant_id = ? 
            ORDER BY updated_at DESC
        """, (employee_id.upper(), tenant_id))
        
        rows = cursor.fetchall()
        session_ids = [r["session_id"] for r in rows]
        conn.close()
        
        sessions = []
        for sid in session_ids:
            sessions.append(self.get_session(sid, tenant_id))
            
        return sessions
