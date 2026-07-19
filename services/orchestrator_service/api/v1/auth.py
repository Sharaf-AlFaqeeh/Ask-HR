from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List
from core.security.sharepoint_mock import authenticate_sharepoint
from core.security.auth import create_access_token, verify_jwt_or_bearer_token, UserPrincipal
from core.security.permissions import get_effective_roles
from core.logger import get_logger

logger = get_logger("auth_api")
router = APIRouter(prefix="/v1/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class UserProfileResponse(BaseModel):
    employee_id: str
    username: str
    first_name: str
    last_name: str
    department: str
    position: str
    email: str
    roles: List[str]

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserProfileResponse

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """
    Authenticates user credentials against SharePoint AD.
    Issues a JWT token on success.
    """
    logger.info(f"Login attempt for: {request.username_or_email}")
    user = authenticate_sharepoint(request.username_or_email, request.password)
    
    if not user:
        logger.warning(f"Failed login attempt for: {request.username_or_email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اسم المستخدم أو كلمة المرور غير صحيحة."
        )
    
    # Retrieve persistent/overridden roles
    effective_roles = get_effective_roles(user["employee_id"], user["roles"])

    # Generate JWT Claims
    token_claims = {
        "sub": user["employee_id"],
        "employee_id": user["employee_id"],
        "tenant_id": user["tenant_id"],
        "roles": effective_roles,
        "scopes": ["read:profile", "write:leave", "read:payslip"]
    }
    
    token = create_access_token(token_claims)
    logger.info(f"Successful login. Issued JWT for employee: {user['employee_id']}")
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfileResponse(
            employee_id=user["employee_id"],
            username=user["username"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            department=user["department"],
            position=user["position"],
            email=user["email"],
            roles=effective_roles
        )
    )

@router.get("/me", response_model=UserProfileResponse)
def get_me(principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)):
    """
    Returns the currently logged-in user profile details by looking up their employee_id.
    """
    from core.security.sharepoint_mock import get_user_by_employee_id
    if not principal.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="الرقم الوظيفي للموظف غير موجود في رمز الوصول."
        )
    user = get_user_by_employee_id(principal.employee_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="لم يتم العثور على ملف الموظف في النظام."
        )
    effective_roles = get_effective_roles(user["employee_id"], user["roles"])
    return UserProfileResponse(
        employee_id=user["employee_id"],
        username=user["username"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        department=user["department"],
        position=user["position"],
        email=user["email"],
        roles=effective_roles
    )
