from typing import Dict, Any, Tuple, Optional, List
from services.orchestrator_service.domain.models import SessionState, PendingAction

class SessionManager:
    """
    Manages conversational session state and implements a multi-turn
    Dialog State Machine to collect required parameters for HR actions.
    """
    
    # Required fields for each intent action
    REQUIRED_FIELDS = {
        "request_leave": ["employee_id", "leave_type", "start_date", "end_date"],
        "get_salary_slip": ["employee_id", "month"],
        "get_profile": ["employee_id"]
    }
    
    # Friendly field names in Arabic for prompting
    FIELD_NAMES_AR = {
        "employee_id": "الرقم الوظيفي (مثال: EMP101)",
        "leave_type": "نوع الإجازة (مثل: إجازة سنوية أو مرضية)",
        "start_date": "تاريخ بدء الإجازة (بالصيغة: YYYY-MM-DD)",
        "end_date": "تاريخ انتهاء الإجازة (بالصيغة: YYYY-MM-DD)",
        "month": "الشهر المستهدف لكشف الراتب (مثال: مايو 2026)"
    }

    # Leave type options for the UI form
    LEAVE_TYPE_OPTIONS = [
        {"value": "ANNUAL_LEAVE", "label_ar": "إجازة سنوية", "label_en": "Annual Leave"},
        {"value": "SICK_LEAVE", "label_ar": "إجازة مرضية", "label_en": "Sick Leave"},
        {"value": "MATERNITY_LEAVE", "label_ar": "إجازة أمومة", "label_en": "Maternity Leave"},
        {"value": "PATERNITY_LEAVE", "label_ar": "إجازة أبوة", "label_en": "Paternity Leave"},
        {"value": "UNPAID_LEAVE", "label_ar": "إجازة بدون راتب", "label_en": "Unpaid Leave"},
    ]

    def process_dialog_turn(
        self, 
        session: SessionState, 
        intent: str, 
        entities: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Processes a dialog turn.
        Returns: Tuple[prompt_for_missing_fields (str), executable_action_params (dict), form_payload (dict)]
        
        - If prompt_for_missing_fields is not None, we should display that prompt to the user (text-based slot filling).
        - If executable_action_params is not None, all required fields are satisfied and we can execute the action.
        - If form_payload is not None, we should render a structured UI form for the user to fill (leave request form).
        """
        # Determine target action name
        action_name = None
        if intent == "SAP":
            # Guess the action from entities or past state
            if entities.get("leave_type") or entities.get("start_date") or entities.get("end_date"):
                action_name = "request_leave"
            elif entities.get("month"):
                action_name = "get_salary_slip"
            elif not session.pending_action:
                # Default to profile lookup only if no specific fields are found AND no action is pending
                action_name = "get_profile"
                
        # 1. Check if we have an active pending action in session
        pending = session.pending_action
        
        # 2. If we have a pending action, merge new entities into it
        if pending:
            # If the user switched intent completely (e.g. from leave request to payslip)
            # and specified the new intent fields explicitly, we might override it.
            # Otherwise, we keep completing the pending action.
            if action_name and action_name != pending.action_name:
                # User changed their mind, start a new pending action
                pending = PendingAction(action_name=action_name)
                session.pending_action = pending
            
            # Merge new extracted entities into the pending action
            for key, val in entities.items():
                if val is not None:
                    pending.parameters[key] = val
        else:
            # If no pending action, but user triggered an SAP action, create one
            if action_name:
                pending = PendingAction(action_name=action_name)
                for key, val in entities.items():
                    if val is not None:
                        pending.parameters[key] = val
                session.pending_action = pending
                
        # 3. Propagate session employee_id if already saved in session
        if pending:
            if session.employee_id and not pending.parameters.get("employee_id"):
                pending.parameters["employee_id"] = session.employee_id

        # 4. If no pending action (e.g. general RAG query), do nothing
        if not pending:
            return None, None, None

        # 5. Evaluate required fields for the active action
        req_fields = self.REQUIRED_FIELDS[pending.action_name]
        missing = [f for f in req_fields if pending.parameters.get(f) is None]
        pending.missing_fields = missing
        
        # Save updated employee_id back to session if it was just provided
        if pending.parameters.get("employee_id"):
            session.employee_id = pending.parameters["employee_id"]

        # 6. If all required fields are collected, execute!
        if not missing:
            params = pending.parameters.copy()
            # Clear pending action since it's fully resolved
            session.pending_action = None
            return None, params, None

        # 7. Otherwise, determine how to prompt for missing fields
        from core.config_manager import get_settings
        settings = get_settings()

        if not settings.sap.mock_mode:
            session.pending_action = None
            prompt = (
                "مرحباً 👋\n\n"
                "حالياً لا يمكنني تنفيذ هذا الإجراء من خلال النظام.\n"
                "لتقديم طلب إجازة أو أي إجراء آخر، يرجى التواصل مع مركز الخدمة للموارد البشرية على الرقم التالي:\n\n"
                "📞 **123456789**\n\n"
                "سيسعد فريق الموارد البشرية بمساعدتك! 😊"
            )
            return prompt, None, None

        # ── NEW: For leave requests with missing dates/type, return a structured form payload ──
        if pending.action_name == "request_leave":
            # Check which leave-specific fields are missing (excluding employee_id)
            leave_missing = [f for f in missing if f != "employee_id"]
            
            if leave_missing:
                # Build form payload with current known values as defaults
                form_payload = self._build_leave_form_payload(pending.parameters)
                
                # If employee_id is the only other missing field, prompt for it via text
                if "employee_id" in missing and len(missing) > len(leave_missing):
                    # We need employee_id too — the form will handle leave fields,
                    # but we still need to prompt for employee_id separately
                    prompt = f"من أجل إتمام تقديم طلب إجازة، يرجى تزويدي بـ {self.FIELD_NAMES_AR['employee_id']}."
                    return prompt, None, form_payload
                
                # If only leave fields are missing (employee_id already known)
                return None, None, form_payload
        
        # ── Standard text-based slot filling for non-leave actions ──
        # If mock_mode is enabled, prompt for the next missing field to run slot-filling
        next_field = missing[0]
        field_desc = self.FIELD_NAMES_AR.get(next_field, next_field)
        
        if pending.action_name == "request_leave":
            action_desc = "تقديم طلب إجازة"
        elif pending.action_name == "get_salary_slip":
            action_desc = "استعلام عن كشف الراتب"
        else:
            action_desc = "عرض الملف الشخصي"

        prompt = f"من أجل إتمام {action_desc}، يرجى تزويدي بـ {field_desc}."
        return prompt, None, None

    def _build_leave_form_payload(self, current_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds a structured leave form payload for the frontend to render.
        Includes current known values as defaults and the full list of leave type options.
        """
        return {
            "form_type": "leave_request",
            "title_ar": "📋 تفاصيل طلب الإجازة",
            "title_en": "Leave Request Details",
            "description_ar": "يرجى مراجعة وتعبئة تفاصيل الإجازة أدناه ثم الضغط على إرسال.",
            "fields": {
                "leave_type": {
                    "label_ar": "نوع الإجازة",
                    "label_en": "Leave Type",
                    "type": "select",
                    "value": current_params.get("leave_type"),
                    "options": self.LEAVE_TYPE_OPTIONS,
                    "required": True
                },
                "start_date": {
                    "label_ar": "تاريخ البداية",
                    "label_en": "Start Date",
                    "type": "date",
                    "value": current_params.get("start_date"),
                    "inferred": False,
                    "required": True
                },
                "end_date": {
                    "label_ar": "تاريخ النهاية",
                    "label_en": "End Date",
                    "type": "date",
                    "value": current_params.get("end_date"),
                    "inferred": False,
                    "required": True
                }
            }
        }
