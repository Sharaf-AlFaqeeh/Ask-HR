from typing import Dict, Optional, List
from services.orchestrator_service.actions.base import BaseHRAction
from services.orchestrator_service.actions.leave_action import LeaveRequestAction
from services.orchestrator_service.actions.payslip_action import PayslipRequestAction
from core.logger import get_logger

logger = get_logger("actions_registry")

class ActionRegistry:
    """
    Registry for managing all HR Actions supported by the AskHR system.
    Supports dynamic registration and lookups.
    """
    def __init__(self):
        self._actions: Dict[str, BaseHRAction] = {}
        logger.info("Initializing HR Action Registry")
        
        # Self-register default out-of-the-box actions
        self.register(LeaveRequestAction())
        self.register(PayslipRequestAction())

    def register(self, action: BaseHRAction) -> None:
        """Registers a new action"""
        action_id = action.action_id
        self._actions[action_id] = action
        logger.info(f"Registered HR Action: {action_id} (Type: {action.action_type.value})")

    def get(self, action_id: str) -> Optional[BaseHRAction]:
        """Looks up and returns an action by its ID"""
        return self._actions.get(action_id)

    def get_all(self) -> Dict[str, BaseHRAction]:
        """Returns all registered actions"""
        return self._actions.copy()

    def get_action_ids(self) -> List[str]:
        """Returns list of registered action IDs"""
        return list(self._actions.keys())

# Global registry singleton
_registry = None

def get_action_registry() -> ActionRegistry:
    """Returns the global ActionRegistry singleton"""
    global _registry
    if _registry is None:
        _registry = ActionRegistry()
    return _registry
