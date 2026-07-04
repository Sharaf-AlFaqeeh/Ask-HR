from typing import Dict, Any, Tuple, Optional, List
from services.orchestrator_service.actions.base import BaseHRAction, ActionType
from services.orchestrator_service.di.container import get_container

class PayslipRequestAction(BaseHRAction):
    """
    Action handling queries for Employee Payroll Slips (from ERP Payroll).
    """

    @property
    def action_id(self) -> str:
        return "get_salary_slip"

    @property
    def action_type(self) -> ActionType:
        return ActionType.INQUIRY

    @property
    def name_ar(self) -> str:
        return "كشف الراتب"

    @property
    def name_en(self) -> str:
        return "Get Salary Slip"

    @property
    def required_fields(self) -> List[str]:
        return ["month"]

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        month = params.get("month")
        if not month:
            return False, "الشهر المستهدف مطلوب للاستعلام عن الراتب."
        return True, None

    def get_ui_template(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "title_ar": "استعلام كشف الراتب",
            "title_en": "Salary Slip Query",
            "month": params["month"],
            # Provide animation/status messages for the frontend to render sequentially
            "status_steps_ar": [
                "جاري الاتصال بنظام SAP SuccessFactors...",
                "جاري التحقق من تفويض الهوية والمستأجر...",
                "جاري تحليل كشف الراتب وسجل الدفعات الخاص بك على نظام SAP..."
            ],
            "status_steps_en": [
                "Connecting to SAP SuccessFactors...",
                "Verifying identity & tenant authorization...",
                "Analyzing your salary history and slip records on SAP..."
            ]
        }

    def execute(self, employee_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        container = get_container()
        # Retrieve the salary details via the SAP adapter client
        response = container.hr_client.get_salary_slip(
            employee_id=employee_id,
            month=params["month"]
        )
        return response.model_dump()
