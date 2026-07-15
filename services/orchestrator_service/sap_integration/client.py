import os
import sys
from typing import Dict, Any, Optional
from pydantic import BaseModel

# Adjust path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from core.logger import get_logger
from core.config_manager import get_settings
from core.exceptions import SAPIntegrationError

logger = get_logger("sap_integration")
settings = get_settings()

class SAPEmployeeProfile(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    department: str
    position: str
    email: str
    status: str

class SAPLeaveRequestResponse(BaseModel):
    request_id: str
    employee_id: str
    leave_type: str
    start_date: str
    end_date: str
    status: str
    message: str

class SAPSalarySlipResponse(BaseModel):
    employee_id: str
    month: str
    basic_salary: float
    housing_allowance: float
    transport_allowance: float
    deductions: float
    net_salary: float

class SAPSuccessFactorsClient:
    """
    Mock client simulating SuccessFactors OData APIs.
    Logs actual payloads that would be sent to real SAP environments.
    """
    def __init__(self):
        self.base_url = settings.sap.api_base_url
        self.mock_mode = settings.sap.mock_mode
        logger.info(
            "Initializing SAP SuccessFactors Client",
            extra_fields={"base_url": self.base_url, "mock_mode": self.mock_mode}
        )

    def get_employee_profile(self, employee_id: str) -> SAPEmployeeProfile:
        """
        Simulates OData GET Request for Employee Profile.
        """
        logger.info(f"SAP HTTP GET: /User('{employee_id}')")
        
        if not employee_id or len(employee_id) < 3:
            raise SAPIntegrationError("Invalid Employee ID provided", details={"employee_id": employee_id})
            
        # Mock database of employees
        mock_db = {
            "EMP101": SAPEmployeeProfile(
                employee_id="EMP101",
                first_name="Sharaf",
                last_name="",
                department="AI",
                position="AI",
                email="sharaf@hsagroup.com",
                status="Active"
            ),
            "EMP102": SAPEmployeeProfile(
                employee_id="EMP102",
                first_name="Khaled",
                last_name="Mutahar",
                department="Technology",
                position="Lead AI Engineer",
                email="khaled.mutahar@hsagroup.com",
                status="Active"
            )
        }
        
        profile = mock_db.get(employee_id.upper())
        if not profile:
            raise SAPIntegrationError(
                f"Employee ID '{employee_id}' not found in SAP SuccessFactors database", 
                details={"employee_id": employee_id}
            )
            
        logger.info(f"SAP HTTP Response: 200 OK - Profile found for {profile.first_name}")
        return profile

    def request_leave(self, employee_id: str, leave_type: str, start_date: str, end_date: str) -> SAPLeaveRequestResponse:
        """
        Simulates OData POST Request to create a Leave Request (TimeOff).
        """
        payload = {
            "userId": employee_id,
            "timeType": leave_type,
            "startDate": start_date,
            "endDate": end_date
        }
        
        logger.info(f"SAP HTTP POST: /EmployeeTime - Payload: {payload}")
        
        # Verify employee first
        self.get_employee_profile(employee_id)
        
        logger.info("SAP HTTP Response: 201 Created - Leave Request successfully registered")
        return SAPLeaveRequestResponse(
            request_id=f"LR-{os.urandom(4).hex().upper()}",
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            status="PENDING_APPROVAL",
            message="Your leave request has been submitted to your manager in SAP SuccessFactors."
        )

    def get_salary_slip(self, employee_id: str, month: str) -> SAPSalarySlipResponse:
        """
        Simulates retrieving payroll data from SuccessFactors/SAP Payroll systems.
        """
        logger.info(f"SAP HTTP GET: /SalarySlip(userId='{employee_id}', month='{month}')")
        
        # Verify employee first
        self.get_employee_profile(employee_id)
        
        # Mock calculation
        basic = 4000.0 if employee_id.upper() == "EMP102" else 2500.0
        housing = basic * 0.25 # 25% housing allowance
        transport = 300.0
        deductions = basic * 0.05 # 5% tax/social security
        net = basic + housing + transport - deductions
        
        logger.info(f"SAP HTTP Response: 200 OK - Salary Slip processed for month: {month}")
        return SAPSalarySlipResponse(
            employee_id=employee_id,
            month=month,
            basic_salary=basic,
            housing_allowance=housing,
            transport_allowance=transport,
            deductions=deductions,
            net_salary=net
        )
