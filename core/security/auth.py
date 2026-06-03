import json
import base64
from typing import Dict, Any, List, Optional
from fastapi import Header, HTTPException, Depends
from core.config_manager import get_settings
from core.exceptions import UnauthorizedError
from core.security.tenant import set_tenant_id

settings = get_settings()

class UserPrincipal:
    """
    Represents the authenticated user context (JWT claims, roles, scopes, tenant).
    """
    def __init__(self, claims: Dict[str, Any]):
        self.claims = claims
        self.employee_id: Optional[str] = claims.get("sub") or claims.get("employee_id")
        self.tenant_id: str = claims.get("tenant_id", "default_tenant")
        self.roles: List[str] = claims.get("roles", [])
        self.scopes: List[str] = claims.get("scopes", [])

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

def decode_jwt_token_unverified(token: str) -> Dict[str, Any]:
    """
    Decodes the JWT payload without verifying the signature.
    Useful for local-first testing and mock environments.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("JWT must have 3 parts")
        
        payload_b64 = parts[1]
        # Pad base64 string if needed
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_json = base64.b64decode(payload_b64).decode("utf-8")
        return json.loads(payload_json)
    except Exception as e:
        raise UnauthorizedError("Invalid JWT token format", details={"error": str(e)})

def verify_jwt_or_bearer_token(authorization: Optional[str] = Header(None)) -> UserPrincipal:
    """
    Verifies the bearer token. Supports:
    1. Standard JWT (decodes tenant_id, employee_id, roles, scopes).
    2. Mock Bearer token (for dev/testing): Maps to a mock user.
    """
    if not authorization:
        raise UnauthorizedError("Missing Authorization Header")
        
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Invalid Authorization format. Expected: 'Bearer <token>'")
        
    token = parts[1]
    
    # Check for local static API Bearer token first (Mock / Dev shortcut)
    if token == settings.api_bearer_token:
        # Return a mock full-privileged UserPrincipal
        claims = {
            "sub": "EMP102", # Khaled (AI Lead) as default admin
            "tenant_id": "HSAGroup",
            "roles": ["employee", "manager", "hr_admin"],
            "scopes": ["read:profile", "write:leave", "read:payslip"]
        }
        principal = UserPrincipal(claims)
        set_tenant_id(principal.tenant_id)
        return principal
        
    # Attempt to decode as JWT
    try:
        # Check if PyJWT is available for signature verification
        try:
            import jwt
            # Verify signature if secret is provided
            payload = jwt.decode(
                token, 
                settings.jwt_secret, 
                algorithms=["HS256"],
                options={"verify_signature": True, "verify_exp": False}
            )
        except ImportError:
            # Fallback to unverified decode for local testing without pyjwt
            payload = decode_jwt_token_unverified(token)
            
        principal = UserPrincipal(payload)
        # Propagate tenant context
        set_tenant_id(principal.tenant_id)
        return principal
    except Exception as ex:
        raise UnauthorizedError(f"Token validation failed: {str(ex)}")

def require_role(required_role: str):
    """
    Dependency injection helper to enforce role-based access control.
    """
    def dependency(principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)) -> UserPrincipal:
        if not principal.has_role(required_role):
            raise HTTPException(
                status_code=403, 
                detail=f"Forbidden: Missing required role '{required_role}'"
            )
        return principal
    return dependency

def require_scope(required_scope: str):
    """
    Dependency injection helper to enforce scope-based access control.
    """
    def dependency(principal: UserPrincipal = Depends(verify_jwt_or_bearer_token)) -> UserPrincipal:
        if not principal.has_scope(required_scope):
            raise HTTPException(
                status_code=403, 
                detail=f"Forbidden: Missing required scope '{required_scope}'"
            )
        return principal
    return dependency
