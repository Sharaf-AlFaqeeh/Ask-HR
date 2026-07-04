from enum import Enum
from typing import Dict, Any, Tuple, Optional, List
from abc import ABC, abstractmethod

class ActionType(str, Enum):
    TRANSACTIONAL = "TRANSACTIONAL"  # Requires user confirmation via verification card
    INQUIRY = "INQUIRY"              # Direct read-only query, shows "Connecting to SAP..." loading card

class BaseHRAction(ABC):
    """
    Abstract base class representing an HR action that can be executed
    against SAP SuccessFactors or simulated.
    """
    
    @property
    @abstractmethod
    def action_id(self) -> str:
        """Unique identifier of the action (e.g., 'request_leave')"""
        pass
        
    @property
    @abstractmethod
    def action_type(self) -> ActionType:
        """Whether this is a transactional action or an inquiry"""
        pass

    @property
    @abstractmethod
    def name_ar(self) -> str:
        """Arabic display name for the action"""
        pass

    @property
    @abstractmethod
    def name_en(self) -> str:
        """English display name for the action"""
        pass

    @property
    @abstractmethod
    def required_fields(self) -> List[str]:
        """List of fields needed to execute this action"""
        pass

    @abstractmethod
    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates the extracted parameters.
        Returns: Tuple[is_valid (bool), error_message (str or None)]
        """
        pass

    @abstractmethod
    def get_ui_template(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates the UI template representation to show in the chat view.
        - For TRANSACTIONAL: Defines the details to verify (labels, values, and submit/cancel buttons).
        - For INQUIRY: Defines the loading messages (e.g. 'Processing your inquiry...') and display format.
        """
        pass

    @abstractmethod
    def execute(self, employee_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the action on SAP SuccessFactors/Mock DB.
        Returns: Dict containing execution result details.
        """
        pass
