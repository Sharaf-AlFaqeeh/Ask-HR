import os
from typing import Dict, Any, Optional
from services.orchestrator_service.domain.interfaces import IHRSystemClient
from services.orchestrator_service.domain.models import (
    EmployeeProfile, LeaveRequestResponse, SalarySlipResponse
)
from core.config_manager import get_settings
from core.logger import get_logger
from core.exceptions import SAPIntegrationError
from core.security.tenant import get_tenant_id

logger = get_logger("sap_client_adapter")
settings = get_settings()

class SAPSuccessFactorsAdapter(IHRSystemClient):
    """
    Adapter implementing the IHRSystemClient port.
    Integrates with SAP SuccessFactors OData APIs.
    Supports a mock simulated mode for local development and real HTTP requests for production.
    """
    def __init__(self):
        self.base_url = settings.sap.api_base_url
        self.mock_mode = settings.sap.mock_mode
        self.company_id = settings.sap.company_id
        logger.info(
            "SAP SuccessFactors Adapter initialized",
            extra_fields={"base_url": self.base_url, "mock_mode": self.mock_mode, "company_id": self.company_id}
        )

    def get_employee_profile(self, employee_id: str) -> EmployeeProfile:
        tenant_id = get_tenant_id()
        logger.info(f"SAP GET User profile for ID: {employee_id} (Tenant: {tenant_id})")

        if not employee_id or len(employee_id) < 3:
            raise SAPIntegrationError("Invalid employee ID", details={"employee_id": employee_id})

        if self.mock_mode:
            # Simulated SAP Database containing tenant specific mapping
            mock_db = {
                "EMP101": EmployeeProfile(
                    employee_id="EMP101",
                    first_name="Ahmed",
                    last_name="Al-Saeed",
                    department="Human Resources",
                    position="HR Specialist",
                    email="ahmed.alsaeed@hsagroup.com",
                    status="Active"
                ),
                "EMP102": EmployeeProfile(
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
                    f"Employee ID '{employee_id}' not found in SAP Database",
                    details={"employee_id": employee_id, "tenant_id": tenant_id}
                )
            return profile
        else:
            # Real OData API logic (scaffolded to showcase real HTTP communication)
            import httpx
            api_endpoint = f"{self.base_url}/User('{employee_id}')"
            headers = {
                "Authorization": f"Bearer {settings.sap_client_secret}",
                "X-Tenant-ID": tenant_id,
                "Accept": "application/json"
            }
            try:
                # Synchronous request simulating OData integration
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(api_endpoint, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        d = data.get("d", data)
                        return EmployeeProfile(
                            employee_id=d.get("userId"),
                            first_name=d.get("firstName"),
                            last_name=d.get("lastName"),
                            department=d.get("department"),
                            position=d.get("title"),
                            email=d.get("email"),
                            status="Active" if d.get("status") == "A" else "Inactive"
                        )
                    elif response.status_code == 404:
                        raise SAPIntegrationError(f"Employee ID '{employee_id}' not found in SuccessFactors")
                    else:
                        raise SAPIntegrationError(f"SAP server returned error {response.status_code}: {response.text}")
            except Exception as e:
                if isinstance(e, SAPIntegrationError):
                    raise e
                raise SAPIntegrationError(f"SAP connection failed: {str(e)}")

    def request_leave(self, employee_id: str, leave_type: str, start_date: str, end_date: str) -> LeaveRequestResponse:
        tenant_id = get_tenant_id()
        logger.info(f"SAP POST Create Leave request for employee: {employee_id} (Tenant: {tenant_id})")

        # Validate employee profile first
        self.get_employee_profile(employee_id)

        if self.mock_mode:
            request_id = f"LR-{os.urandom(4).hex().upper()}"
            return LeaveRequestResponse(
                request_id=request_id,
                employee_id=employee_id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                status="PENDING_APPROVAL",
                message=f"Leave request registered successfully on mock SuccessFactors. Request ID: {request_id}"
            )
        else:
            import httpx
            api_endpoint = f"{self.base_url}/EmployeeTime"
            payload = {
                "userId": employee_id,
                "timeType": leave_type,
                "startDate": f"/Date({start_date})/",  # OData date format
                "endDate": f"/Date({end_date})/"
            }
            headers = {
                "Authorization": f"Bearer {settings.sap_client_secret}",
                "X-Tenant-ID": tenant_id,
                "Content-Type": "application/json"
            }
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(api_endpoint, json=payload, headers=headers)
                    if response.status_code in [200, 201]:
                        data = response.json().get("d", {})
                        return LeaveRequestResponse(
                            request_id=data.get("externalCode", f"LR-{os.urandom(3).hex().upper()}"),
                            employee_id=employee_id,
                            leave_type=leave_type,
                            start_date=start_date,
                            end_date=end_date,
                            status="PENDING_APPROVAL",
                            message="Leave request submitted successfully via SuccessFactors OData API."
                        )
                    else:
                        raise SAPIntegrationError(f"SAP Leave registration failed: {response.text}")
            except Exception as e:
                if isinstance(e, SAPIntegrationError):
                    raise e
                raise SAPIntegrationError(f"SAP network connection failed: {str(e)}")

    def get_salary_slip(self, employee_id: str, month: str) -> SalarySlipResponse:
        tenant_id = get_tenant_id()
        logger.info(f"SAP GET Payroll slip for Employee: {employee_id}, Month: {month} (Tenant: {tenant_id})")

        # Validate employee
        self.get_employee_profile(employee_id)

        if self.mock_mode:
            # Mock calculations
            basic = 4000.0 if employee_id.upper() == "EMP102" else 2500.0
            housing = basic * 0.25
            transport = 300.0
            deductions = basic * 0.05
            net = basic + housing + transport - deductions
            
            return SalarySlipResponse(
                employee_id=employee_id,
                month=month,
                basic_salary=basic,
                housing_allowance=housing,
                transport_allowance=transport,
                deductions=deductions,
                net_salary=net
            )
        else:
            # In real system, this would query the ERP payroll backend
            import httpx
            api_endpoint = f"{self.base_url}/SalarySlip(userId='{employee_id}',month='{month}')"
            headers = {
                "Authorization": f"Bearer {settings.sap_client_secret}",
                "X-Tenant-ID": tenant_id
            }
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(api_endpoint, headers=headers)
                    if response.status_code == 200:
                        data = response.json().get("d", {})
                        return SalarySlipResponse(
                            employee_id=employee_id,
                            month=month,
                            basic_salary=float(data.get("basic", 0.0)),
                            housing_allowance=float(data.get("housing", 0.0)),
                            transport_allowance=float(data.get("transport", 0.0)),
                            deductions=float(data.get("deductions", 0.0)),
                            net_salary=float(data.get("net", 0.0))
                        )
                    else:
                        # Fallback calculation if payslip endpoint is not fully configured in SF, to avoid blocking UI
                        raise SAPIntegrationError(f"SAP Payroll API returned error {response.status_code}: {response.text}")
            except Exception as e:
                if isinstance(e, SAPIntegrationError):
                    raise e
                raise SAPIntegrationError(f"SAP connection failed: {str(e)}")
