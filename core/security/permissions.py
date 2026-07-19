from typing import List, Dict, Any
from fastapi import Depends, HTTPException, status
from core.security.auth import verify_jwt_or_bearer_token, UserPrincipal
from core.security.permissions_store import PermissionsStore

# Role definitions
ROLE_GENERAL_MANAGER = "general_manager"
ROLE_HR_ADMIN = "hr_admin"
ROLE_MANAGER = "manager"
ROLE_EMPLOYEE = "employee"

# Permission definitions
PERM_VIEW_OVERVIEW = "view_overview"
PERM_UPDATE_INDEX = "update_index"
PERM_VIEW_SETTINGS = "view_settings"
PERM_MANAGE_PERMISSIONS = "manage_permissions"
PERM_DELETE_SESSION = "delete_session"

# Default role-to-permissions mapping
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    ROLE_GENERAL_MANAGER: [
        PERM_VIEW_OVERVIEW,
        PERM_UPDATE_INDEX,
        PERM_VIEW_SETTINGS,
        PERM_MANAGE_PERMISSIONS,
        PERM_DELETE_SESSION
    ],
    ROLE_HR_ADMIN: [
        PERM_VIEW_OVERVIEW,
        PERM_UPDATE_INDEX,
        PERM_VIEW_SETTINGS,
        PERM_DELETE_SESSION
    ],
    ROLE_MANAGER: [
        PERM_VIEW_OVERVIEW
    ],
    ROLE_EMPLOYEE: []
}

# Global permissions store instance
_store = PermissionsStore()

def has_permission(user_roles: List[str], required_permission: str) -> bool:
    """
    Checks if any of the user's roles grant the required permission.
    """
    for role in user_roles:
        permissions = ROLE_PERMISSIONS.get(role, [])
        if required_permission in permissions:
            return True
    return False

def get_user_permissions(user_roles: List[str]) -> List[str]:
    """
    Returns the compiled list of unique permissions for the given roles.
    """
    compiled = set()
    for role in user_roles:
        compiled.update(ROLE_PERMISSIONS.get(role, []))
    return list(compiled)

def require_permission(required_permission: str):
    """
    FastAPI dependency to enforce permission-based access control.
    """
    def dependency(principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)) -> UserPrincipal:
        if not has_permission(principal.roles, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"غير مصرح: الحساب لا يملك صلاحية '{required_permission}'"
            )
        return principal
    return dependency

def get_effective_roles(employee_id: str, default_roles: List[str]) -> List[str]:
    """
    Returns custom roles if defined in the store, otherwise falls back to defaults.
    """
    custom = _store.get_user_roles(employee_id)
    if custom is not None:
        return custom
    return default_roles

def save_custom_roles(employee_id: str, roles: List[str]) -> None:
    """
    Updates user roles in the database.
    """
    _store.save_user_roles(employee_id, roles)

def reset_custom_roles(employee_id: str) -> None:
    """
    Clears custom role assignments.
    """
    _store.clear_user_roles(employee_id)
