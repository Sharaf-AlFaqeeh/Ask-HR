from typing import Dict, Any, Optional

# Mock User Directory simulating SharePoint Active Directory linked to SAP SuccessFactors
MOCK_USERS_DIRECTORY: Dict[str, Dict[str, Any]] = {
    "ahmed.alsaeed@hsagroup.com": {
        "employee_id": "EMP101",
        "username": "ahmed.alsaeed",
        "password": "password123",
        "first_name": "Ahmed",
        "last_name": "Al-Saeed",
        "department": "Human Resources",
        "position": "HR Specialist",
        "email": "ahmed.alsaeed@hsagroup.com",
        "roles": ["employee", "hr_admin"],
        "tenant_id": "HSAGroup",
        "leave_balance": {"annual": 25, "sick": 14, "unpaid": 30}
    },
    "khaled.mutahar@hsagroup.com": {
        "employee_id": "EMP102",
        "username": "khaled.mutahar",
        "password": "password123",
        "first_name": "Khaled",
        "last_name": "Mutahar",
        "department": "Technology",
        "position": "Lead AI Engineer",
        "email": "khaled.mutahar@hsagroup.com",
        "roles": ["employee", "manager"],
        "tenant_id": "HSAGroup",
        "leave_balance": {"annual": 18, "sick": 15, "unpaid": 30}
    },
    "sarah.jamil@hsagroup.com": {
        "employee_id": "EMP103",
        "username": "sarah.jamil",
        "password": "password123",
        "first_name": "Sarah",
        "last_name": "Jamil",
        "department": "Finance",
        "position": "Financial Analyst",
        "email": "sarah.jamil@hsagroup.com",
        "roles": ["employee"],
        "tenant_id": "HSAGroup",
        "leave_balance": {"annual": 30, "sick": 10, "unpaid": 30}
    },
    "ali.mansoor@hsagroup.com": {
        "employee_id": "EMP104",
        "username": "ali.mansoor",
        "password": "password123",
        "first_name": "Ali",
        "last_name": "Mansoor",
        "department": "Sales",
        "position": "Sales Representative",
        "email": "ali.mansoor@hsagroup.com",
        "roles": ["employee"],
        "tenant_id": "HSAGroup",
        "leave_balance": {"annual": 20, "sick": 12, "unpaid": 30}
    }
}

# Allow username as alternative lookup key
USER_LOOKUP_MAP: Dict[str, str] = {
    user["username"]: email for email, user in MOCK_USERS_DIRECTORY.items()
}

def authenticate_sharepoint(username_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verifies user credentials against the mock SharePoint Active Directory.
    Returns user details (without password) if successful, otherwise None.
    """
    cleaned_key = username_or_email.strip().lower()
    
    # Resolve email if username was provided
    email = cleaned_key
    if "@" not in cleaned_key:
        email = USER_LOOKUP_MAP.get(cleaned_key)
        if not email:
            return None
            
    user_info = MOCK_USERS_DIRECTORY.get(email)
    if not user_info:
        return None
        
    if user_info["password"] == password:
        # Return a copy without password
        result = user_info.copy()
        del result["password"]
        return result
        
    return None

def get_user_by_employee_id(employee_id: str) -> Optional[Dict[str, Any]]:
    """
    Helper to fetch a mock user profile by their SAP Employee ID.
    """
    emp_id_upper = employee_id.upper()
    for user in MOCK_USERS_DIRECTORY.values():
        if user["employee_id"] == emp_id_upper:
            result = user.copy()
            del result["password"]
            return result
    return None
