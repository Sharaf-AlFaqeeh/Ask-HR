import time
from typing import Dict, Any, List, Optional
from services.orchestrator_service.domain.models import SessionState, Message
from services.orchestrator_service.domain.interfaces import (
    ILLMClient, IRetriever, IHRSystemClient, ISessionStore, INLPPipeline
)
from services.orchestrator_service.application.session_manager import SessionManager
from core.logger import get_logger

logger = get_logger("flow_orchestrator")

class FlowOrchestrator:
    """
    Coordinates the business flow: Session Retrieval -> NLP Analysis ->
    Dialog State Decision -> Action Execution (SAP/RAG) -> LLM Synthesis -> Session Save.
    """
    def __init__(
        self,
        llm_client: ILLMClient,
        retriever: IRetriever,
        hr_client: IHRSystemClient,
        session_store: ISessionStore,
        nlp_pipeline: INLPPipeline
    ):
        self.llm_client = llm_client
        self.retriever = retriever
        self.hr_client = hr_client
        self.session_store = session_store
        self.nlp_pipeline = nlp_pipeline
        self.dialog_manager = SessionManager()

    async def handle_message(
        self, 
        session_id: str, 
        tenant_id: str, 
        query: str,
        override_employee_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing a single user query within a session context.
        """
        logger.info(
            f"Processing message in flow orchestrator", 
            extra_fields={"session_id": session_id, "tenant_id": tenant_id, "query": query}
        )

        # 1. Retrieve or create session state
        session = self.session_store.get_session(session_id, tenant_id)
        session.add_message(role="user", content=query)
        
        # Override employee ID if explicitly provided in request body
        if override_employee_id:
            session.employee_id = override_employee_id.upper()

        # 2. Run Intent Routing and Entity Extraction
        intent, confidence, entities = await self.nlp_pipeline.analyze_query(query)
        
        # If there is a pending SAP action, we assume the user is continuing the SAP dialog flow
        if session.pending_action and intent != "SAP":
            logger.info(
                f"Active pending action '{session.pending_action.action_name}' found. "
                "Forcing SAP context to process parameter filling."
            )
            intent = "SAP"
            confidence = 1.0

        # 3. Pass to Dialog Manager (Slot Filling / Dialog state)
        missing_prompt, action_params = self.dialog_manager.process_dialog_turn(
            session=session,
            intent=intent,
            entities=entities
        )

        response_text = ""
        context_used = False
        sap_executed = False
        execution_details = {}

        # 4. If missing details, prompt the user
        if missing_prompt:
            response_text = missing_prompt
            session.add_message(role="assistant", content=response_text)
            self.session_store.save_session(session)
            
            return self._build_response_payload(
                query=query,
                intent=intent,
                confidence=confidence,
                entities=entities,
                response=response_text,
                context_used=context_used,
                sap_executed=sap_executed,
                session_pending=True
            )

        # 5. If SAP Action is fully qualified, execute it!
        if action_params:
            sap_executed = True
            action_name = session.pending_action.action_name if session.pending_action else "get_profile"
            if "leave_type" in action_params and "start_date" in action_params:
                action_name = "request_leave"
            elif "month" in action_params:
                action_name = "get_salary_slip"
                
            emp_id = action_params.get("employee_id")
            
            logger.info(f"Executing SAP Action: {action_name} for employee: {emp_id}")
            
            try:
                if action_name == "request_leave":
                    leave_res = self.hr_client.request_leave(
                        employee_id=emp_id,
                        leave_type=action_params.get("leave_type"),
                        start_date=action_params.get("start_date"),
                        end_date=action_params.get("end_date")
                    )
                    execution_details = leave_res.model_dump()
                    
                    # LLM ground response building
                    llm_instruction = (
                        "أنت مساعد موارد بشرية ذكي لمجموعة هائل سعيد أنعم (HSA Group).\n"
                        "قم بصياغة استجابة باللغة العربية الفصحى تؤكد فيها نجاح تقديم طلب الإجازة في نظام SAP SuccessFactors بالبيانات التالية:\n"
                        f"- رقم الطلب: {leave_res.request_id}\n"
                        f"- الرقم الوظيفي للموظف: {emp_id}\n"
                        f"- نوع الإجازة: {leave_res.leave_type}\n"
                        f"- الفترة: من {leave_res.start_date} إلى {leave_res.end_date}\n"
                        f"- حالة الطلب: {leave_res.status}\n"
                        f"- رسالة التأكيد من SAP: {leave_res.message}\n"
                    )
                    response_text = await self.llm_client.query_llm([
                        {"role": "system", "content": "أنت خبير خدمة عملاء الموارد البشرية لمجموعة HSA Group."},
                        {"role": "user", "content": llm_instruction}
                    ])
                    
                elif action_name == "get_salary_slip":
                    salary_res = self.hr_client.get_salary_slip(
                        employee_id=emp_id,
                        month=action_params.get("month")
                    )
                    execution_details = salary_res.model_dump()
                    
                    llm_instruction = (
                        "أنت مساعد موارد بشرية ذكي لمجموعة هائل سعيد أنعم (HSA Group).\n"
                        "قم بصياغة استجابة باللغة العربية الفصحى تؤكد فيها تفاصيل كشف الراتب (Payslip) المسترجع للموظف من نظام SAP SuccessFactors:\n"
                        f"بيانات كشف الراتب للموظف {emp_id} عن شهر {salary_res.month}:\n"
                        f"- الراتب الأساسي: {salary_res.basic_salary} USD\n"
                        f"- بدل السكن: {salary_res.housing_allowance} USD\n"
                        f"- بدل المواصلات: {salary_res.transport_allowance} USD\n"
                        f"- الاستقطاعات: {salary_res.deductions} USD\n"
                        f"- صافي الراتب: {salary_res.net_salary} USD\n"
                    )
                    response_text = await self.llm_client.query_llm([
                        {"role": "system", "content": "أنت خبير خدمة عملاء الموارد البشرية لمجموعة HSA Group."},
                        {"role": "user", "content": llm_instruction}
                    ])
                    
                else: # get_profile
                    profile_res = self.hr_client.get_employee_profile(employee_id=emp_id)
                    execution_details = profile_res.model_dump()
                    
                    llm_instruction = (
                        "أنت مساعد موارد بشرية ذكي لمجموعة هائل سعيد أنعم (HSA Group).\n"
                        "قم بصياغة تحية دافئة وتأكيد قراءة ملف الموظف المسترجع من SAP SuccessFactors باللغة العربية الفصحى:\n"
                        f"- الاسم: {profile_res.first_name} {profile_res.last_name}\n"
                        f"- الإدارة: {profile_res.department}\n"
                        f"- المسمى الوظيفي: {profile_res.position}\n"
                        f"- البريد الإلكتروني: {profile_res.email}\n"
                        f"- حالة الحساب: {profile_res.status}\n"
                        "اسأل الموظف بلطف كيف يمكنك مساعدته اليوم في كشوف المرتبات أو تقديم إجازة."
                    )
                    response_text = await self.llm_client.query_llm([
                        {"role": "system", "content": "أنت خبير خدمة عملاء الموارد البشرية لمجموعة HSA Group."},
                        {"role": "user", "content": llm_instruction}
                    ])
            except Exception as ex:
                logger.error(f"Error executing SAP action: {str(ex)}", exc_info=True)
                response_text = f"عذراً، حدث خطأ أثناء تنفيذ الإجراء في نظام SAP SuccessFactors: {str(ex)}"
                execution_details = {"error": str(ex)}

        # 6. RAG Pipeline execution (General Policies)
        else:
            logger.info("Running RAG context retrieval...")
            context = self.retriever.retrieve_context(query)
            
            if context:
                context_used = True
                system_instructions = (
                    "أنت خبير محترف ومستشار الموارد البشرية لمجموعة هائل سعيد أنعم (HSA Group).\n"
                    "مهمتك هي الإجابة بدقة وأمانة على استفسارات الموظف باستخدام السياق المسترجع المرفق فقط.\n"
                    "اتبع القواعد التالية بدقة:\n"
                    "1. إذا لم تجد الإجابة في السياق المرفق، قل بوضوح ولطف: 'عذراً، لم أجد إجابة دقيقة لهذا الاستفسار في لوائح سياسات الموارد البشرية الحالية، يرجى التواصل مع إدارة الموارد البشرية مباشرة.'\n"
                    "2. لا تقم أبداً باختلاق أو تخمين أي سياسات أو تواريخ أو أرقام غير موجودة في السياق المرفق.\n"
                    "3. أجب بلغة مهنية وودودة للغاية باللغة العربية الفصحى.\n\n"
                    "السياق المسترجع من اللوائح والسياسات الرسمية لمجموعة HSA:\n"
                    "=========================================\n"
                    f"{context}\n"
                    "=========================================\n"
                )
                
                # Assemble conversation context including history for better multi-turn interaction
                messages = [{"role": "system", "content": system_instructions}]
                # Append last few messages of history for conversational context (limit to last 5 for tokens)
                for hist_msg in session.history[-6:-1]:
                    messages.append({"role": hist_msg.role, "content": hist_msg.content})
                messages.append({"role": "user", "content": query})
                
                response_text = await self.llm_client.query_llm(messages)
            else:
                logger.warning("No context found in RAG collection. Falling back to default assistant prompt.")
                messages = [
                    {"role": "system", "content": "أنت مساعد الموارد البشرية لمجموعة هائل سعيد أنعم (HSA Group). أجب بلطف وبأسلوب مهني."},
                    {"role": "user", "content": query}
                ]
                response_text = await self.llm_client.query_llm(messages)

        # 7. Update and save session history
        session.add_message(role="assistant", content=response_text)
        self.session_store.save_session(session)

        return self._build_response_payload(
            query=query,
            intent=intent,
            confidence=confidence,
            entities=entities,
            response=response_text,
            context_used=context_used,
            sap_executed=sap_executed,
            session_pending=session.pending_action is not None,
            execution_details=execution_details
        )

    def _build_response_payload(
        self,
        query: str,
        intent: str,
        confidence: float,
        entities: Dict[str, Any],
        response: str,
        context_used: bool,
        sap_executed: bool,
        session_pending: bool,
        execution_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return {
            "query": query,
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
            "response": response,
            "context_used": context_used,
            "sap_executed": sap_executed,
            "session_pending": session_pending,
            "execution_details": execution_details or {}
        }
