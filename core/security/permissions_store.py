import sqlite3
import json
import time
from typing import List, Optional
from core.logger import get_logger

logger = get_logger("permissions_store")

class PermissionsStore:
    """
    Handles persisting and retrieving custom user roles in the database.
    Allows General Manager to override employee roles dynamically.
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                employee_id TEXT PRIMARY KEY,
                roles TEXT, -- JSON array of roles
                updated_at REAL
            )
        """)
        conn.commit()
        conn.close()
        logger.info("PermissionsStore database initialized.")

    def get_user_roles(self, employee_id: str) -> Optional[List[str]]:
        """
        Retrieves custom roles assigned to the employee. Returns None if default mock applies.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT roles FROM user_roles WHERE employee_id = ?", (employee_id.upper(),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                return json.loads(row["roles"])
            except Exception as e:
                logger.error(f"Error parsing user roles for {employee_id}: {e}")
        return None

    def save_user_roles(self, employee_id: str, roles: List[str]) -> None:
        """
        Saves or updates custom roles for the employee.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        roles_json = json.dumps(roles)
        cursor.execute("""
            INSERT OR REPLACE INTO user_roles (employee_id, roles, updated_at)
            VALUES (?, ?, ?)
        """, (employee_id.upper(), roles_json, time.time()))
        conn.commit()
        conn.close()
        logger.info(f"Saved custom roles {roles} for user {employee_id}")

    def clear_user_roles(self, employee_id: str) -> None:
        """
        Reverts the user to default mock active directory roles.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_roles WHERE employee_id = ?", (employee_id.upper(),))
        conn.commit()
        conn.close()
        logger.info(f"Cleared custom roles for user {employee_id}")
