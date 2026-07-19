from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any
from core.security.auth import verify_jwt_or_bearer_token, UserPrincipal
from core.security.permissions import (
    has_permission, 
    get_effective_roles, 
    save_custom_roles, 
    reset_custom_roles,
    PERM_MANAGE_PERMISSIONS,
    ROLE_PERMISSIONS
)
from core.security.sharepoint_mock import MOCK_USERS_DIRECTORY
from core.logger import get_logger

logger = get_logger("permissions_api")
router = APIRouter(prefix="/v1/permissions", tags=["permissions"])

class UserRolesUpdate(BaseModel):
    employee_id: str
    roles: List[str]

@router.get("/users")
def get_all_users(principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)):
    """
    Returns all users and their effective roles.
    Only users with permission 'manage_permissions' (like General Manager) can retrieve this list.
    """
    if not has_permission(principal.roles, PERM_MANAGE_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="غير مصرح لك باسترجاع قائمة المستخدمين وصلاحياتهم."
        )

    users_list = []
    for email, user in MOCK_USERS_DIRECTORY.items():
        effective_roles = get_effective_roles(user["employee_id"], user["roles"])
        users_list.append({
            "employee_id": user["employee_id"],
            "username": user["username"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "department": user["department"],
            "position": user["position"],
            "email": user["email"],
            "roles": effective_roles
        })
    
    return {
        "users": users_list,
        "available_roles": list(ROLE_PERMISSIONS.keys())
    }

@router.post("/update")
def update_user_roles(
    request: UserRolesUpdate,
    principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)
):
    """
    Updates a user's roles.
    Only the General Manager (or users with manage_permissions) can distribute permissions.
    """
    if not has_permission(principal.roles, PERM_MANAGE_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="غير مصرح لك بتحديث صلاحيات المستخدمين."
        )

    # Validate that roles exist
    for role in request.roles:
        if role not in ROLE_PERMISSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"الدور المحدد غير صالح: {role}"
            )

    # Verify user exists in mock directory
    from core.security.sharepoint_mock import get_user_by_employee_id
    user = get_user_by_employee_id(request.employee_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="لم يتم العثور على الموظف المحدد."
        )

    # Prevent General Manager from locking themselves out of the system
    # (i.e. GM cannot demote themselves to a role without manage_permissions)
    if request.employee_id and principal.employee_id and request.employee_id.upper() == principal.employee_id.upper():
        if not any(has_permission([r], PERM_MANAGE_PERMISSIONS) for r in request.roles):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="لا يمكنك إلغاء صلاحية إدارة النظام عن نفسك لمنع حظر الحساب."
            )

    # Save to SQLite
    save_custom_roles(request.employee_id, request.roles)
    logger.info(f"User {principal.employee_id} updated roles for employee {request.employee_id} to {request.roles}")
    
    return {
        "success": True, 
        "message": f"تم تحديث صلاحيات الموظف {user['first_name']} بنجاح."
    }
