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

    def process_dialog_turn(
        self, 
        session: SessionState, 
        intent: str, 
        entities: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Processes a dialog turn.
        Returns: Tuple[prompt_for_missing_fields (str), executable_action_params (dict)]
        If prompt_for_missing_fields is not None, we should display that prompt to the user.
        If executable_action_params is not None, all required fields are satisfied and we can execute the action.
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
            return None, None

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
            return None, params

        # 7. Otherwise, formulate a friendly prompt for the first missing field
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
            return prompt, None

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
        return prompt, None
