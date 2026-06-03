from contextvars import ContextVar
from typing import Optional

# Context variable to store the current tenant ID
_current_tenant_id: ContextVar[str] = ContextVar("current_tenant_id", default="default_tenant")

def get_tenant_id() -> str:
    """
    Retrieves the tenant ID for the current request context.
    """
    return _current_tenant_id.get()

def set_tenant_id(tenant_id: str) -> None:
    """
    Sets the tenant ID for the current request context.
    """
    _current_tenant_id.set(tenant_id)

def clear_tenant_id() -> None:
    """
    Resets the tenant ID to the default.
    """
    _current_tenant_id.set("default_tenant")
