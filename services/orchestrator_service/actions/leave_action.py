from typing import Dict, Any, Tuple, Optional, List
from services.orchestrator_service.actions.base import BaseHRAction, ActionType
from services.orchestrator_service.di.container import get_container
from datetime import datetime

class LeaveRequestAction(BaseHRAction):
    """
    Action handling HR Leave Requests (TimeOff in SuccessFactors).
    """

    @property
    def action_id(self) -> str:
        return "request_leave"

    @property
    def action_type(self) -> ActionType:
        return ActionType.TRANSACTIONAL

    @property
    def name_ar(self) -> str:
        return "تقديم طلب إجازة"

    @property
    def name_en(self) -> str:
        return "Submit Leave Request"

    @property
    def required_fields(self) -> List[str]:
        return ["leave_type", "start_date", "end_date"]

    def validate(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        start_date_str = params.get("start_date")
        end_date_str = params.get("end_date")
        
        if not start_date_str or not end_date_str:
            return False, "تاريخ البدء وتاريخ الانتهاء مطلوبان."
            
        try:
            # Parse dates to validate formats and ranges
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            
            if end_date < start_date:
                return False, "تاريخ انتهاء الإجازة لا يمكن أن يكون قبل تاريخ البدء."
                
            # Basic validation check: is it in the future?
            # (Optional, but good for robust testing)
            
        except ValueError:
            return False, "تنسيق التاريخ غير صالح. يرجى استخدام الصيغة YYYY-MM-DD (مثال: 2026-08-01)."

        return True, None

    def get_ui_template(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Calculate total days if dates are valid
        total_days = "غير محدد"
        try:
            start = datetime.strptime(params["start_date"], "%Y-%m-%d")
            end = datetime.strptime(params["end_date"], "%Y-%m-%d")
            total_days = f"{(end - start).days + 1} أيام"
        except Exception:
            pass

        # Translate leave types into friendly Arabic names
        leave_translations = {
            "ANNUAL_LEAVE": "إجازة سنوية",
            "SICK_LEAVE": "إجازة مرضية",
            "MATERNITY_LEAVE": "إجازة وضع/أمومة",
            "PATERNITY_LEAVE": "إجازة أبوة",
            "UNPAID_LEAVE": "إجازة بدون راتب"
        }
        raw_type = params.get("leave_type", "")
        leave_name_ar = leave_translations.get(raw_type.upper(), raw_type)

        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "title_ar": "مراجعة وتأكيد طلب الإجازة",
            "title_en": "Confirm Leave Request",
            "summary_ar": f"أنت على وشك تقديم طلب لـ {leave_name_ar} في نظام SAP SuccessFactors.",
            "fields": [
                {"label_ar": "نوع الإجازة", "label_en": "Leave Type", "value": leave_name_ar, "key": "leave_type"},
                {"label_ar": "تاريخ البدء", "label_en": "Start Date", "value": params["start_date"], "key": "start_date"},
                {"label_ar": "تاريخ الانتهاء", "label_en": "End Date", "value": params["end_date"], "key": "end_date"},
                {"label_ar": "إجمالي المدة", "label_en": "Total Duration", "value": total_days, "key": "duration"}
            ],
            "buttons": [
                {"label_ar": "تأكيد وإرسال (Submit)", "label_en": "Confirm & Submit", "event": "submit", "style": "primary"},
                {"label_ar": "إلغاء الطلب", "label_en": "Cancel", "event": "cancel", "style": "secondary"}
            ]
        }

    def execute(self, employee_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        container = get_container()
        # Call the configured SAP successfactors client via adapter
        response = container.hr_client.request_leave(
            employee_id=employee_id,
            leave_type=params["leave_type"],
            start_date=params["start_date"],
            end_date=params["end_date"]
        )
        return response.model_dump()
