class ResponseTemplates:
    """
    Hardcoded, fast, and 100% accurate Arabic response templates for SAP SuccessFactors actions.
    Used when the configuration disables LLM synthesis for SAP transactions to save time/tokens.
    """

    @staticmethod
    def get_leave_response(request_id: str, employee_id: str, leave_type: str, start_date: str, end_date: str, status: str, message: str) -> str:
        # Convert leave type to a friendly Arabic name if possible
        leave_type_ar = {
            "ANNUAL_LEAVE": "إجازة سنوية",
            "SICK_LEAVE": "إجازة مرضية",
            "MATERNITY_LEAVE": "إجازة أمومة",
            "PATERNITY_LEAVE": "إجازة أبوة",
            "UNPAID_LEAVE": "إجازة بدون راتب"
        }.get(leave_type, leave_type)

        return (
            f"✅ تم تقديم طلب الإجازة بنجاح في نظام SAP SuccessFactors.\n\n"
            f"تفاصيل الطلب:\n"
            f"- رقم الطلب: {request_id}\n"
            f"- الرقم الوظيفي: {employee_id}\n"
            f"- نوع الإجازة: {leave_type_ar}\n"
            f"- الفترة: من {start_date} إلى {end_date}\n"
            f"- حالة الطلب: {status}\n"
            f"- رسالة التأكيد: {message}"
        )

    @staticmethod
    def get_salary_slip_response(employee_id: str, month: str, basic_salary: float, housing_allowance: float, transport_allowance: float, deductions: float, net_salary: float) -> str:
        return (
            f"📊 تفاصيل كشف الراتب (Payslip) المسترجع للموظف {employee_id} عن شهر {month}:\n\n"
            f"- الراتب الأساسي: {basic_salary} USD\n"
            f"- بدل السكن: {housing_allowance} USD\n"
            f"- بدل المواصلات: {transport_allowance} USD\n"
            f"- الاستقطاعات: {deductions} USD\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💰 صافي الراتب: {net_salary} USD"
        )

    @staticmethod
    def get_profile_response(first_name: str, last_name: str, department: str, position: str, email: str, status: str) -> str:
        return (
            f"👤 مرحباً بك! تم استرجاع ملفك الشخصي بنجاح من نظام SAP:\n\n"
            f"- الاسم الكامل: {first_name} {last_name}\n"
            f"- الإدارة: {department}\n"
            f"- المسمى الوظيفي: {position}\n"
            f"- البريد الإلكتروني: {email}\n"
            f"- حالة الحساب: {status}\n\n"
            f"كيف يمكنني مساعدتك اليوم؟ (مثال: طلب إجازة، أو استعلام عن كشف راتب)"
        )
