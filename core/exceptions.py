from typing import Any, Dict, Optional

class AskHRException(Exception):
    """Base Exception class for the AskHR system"""
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class ConfigurationError(AskHRException):
    """Raised when application configuration is missing or invalid"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)

class LLMInferenceError(AskHRException):
    """Raised when there is an error in local llama-cpp model loading or inference"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=502, details=details)

class VectorDBError(AskHRException):
    """Raised when Qdrant database or embedding pipeline fails"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)

class IntentRoutingError(AskHRException):
    """Raised when the Intent Router fails to analyze queries"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)

class EntityExtractionError(AskHRException):
    """Raised when entity extraction fails or gets invalid entities for SAP"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=422, details=details)

class SAPIntegrationError(AskHRException):
    """Raised when simulated or real SAP SuccessFactors integrations fail"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=502, details=details)

class UnauthorizedError(AskHRException):
    """Raised when security bearer tokens are missing or invalid"""
    def __init__(self, message: str = "Unauthorized access to AskHR Orchestrator", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)
