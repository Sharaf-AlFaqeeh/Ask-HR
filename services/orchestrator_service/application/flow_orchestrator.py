import time
from typing import Dict, Any, List, Optional
from services.orchestrator_service.domain.models import SessionState, Message
from services.orchestrator_service.domain.interfaces import (
    ILLMClient, IRetriever, IHRSystemClient, ISessionStore, INLPPipeline
)
from services.orchestrator_service.application.session_manager import SessionManager
from services.orchestrator_service.application.prompt_registry import PromptRegistry
from services.orchestrator_service.application.response_templates import ResponseTemplates
from core.config_manager import get_settings
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
        self.settings = get_settings()

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
        start_time = time.time()
        logger.info(
            f"Processing message in flow orchestrator", 
            extra_fields={"session_id": session_id, "tenant_id": tenant_id, "query": query}
        )

        # 1. Retrieve or create session state
        session_start = time.time()
        session = self.session_store.get_session(session_id, tenant_id)
        session.add_message(role="user", content=query)
        
        # Override employee ID if explicitly provided in request body
        if override_employee_id:
            session.employee_id = override_employee_id.upper()
        session_duration = time.time() - session_start

        # 2. Run Intent Routing and Entity Extraction
        nlp_start = time.time()
        has_pending = session.pending_action is not None
        intent, confidence, entities = await self.nlp_pipeline.analyze_query(query, has_pending_action=has_pending)
        
        # If there is a pending SAP action, we assume the user is continuing the SAP dialog flow
        if session.pending_action and intent != "SAP":
            logger.info(
                f"Active pending action '{session.pending_action.action_name}' found. "
                "Forcing SAP context to process parameter filling."
            )
            intent = "SAP"
            confidence = 1.0
        nlp_duration = time.time() - nlp_start

        # 2.5. Intercept SAP actions — system cannot process transactional requests yet.
        #      Redirect the user to contact HR directly via phone.
        if intent == "SAP":
            redirect_response = (
                "مرحباً 👋\n\n"
                "حالياً لا يمكنني تنفيذ هذا الإجراء من خلال النظام.\n"
                "لتقديم طلب إجازة أو أي إجراء آخر، يرجى التواصل مع قسم الموارد البشرية على الرقم التالي:\n\n"
                "📞 **123456789**\n\n"
                "سيسعد فريق الموارد البشرية بمساعدتك! 😊"
            )
            session.add_message(role="assistant", content=redirect_response)
            # Clear any pending SAP action to avoid stale state
            session.pending_action = None
            self.session_store.save_session(session)

            total_duration = time.time() - start_time
            logger.info(
                f"SAP action intercepted — redirecting user to HR phone contact. "
                f"total={total_duration:.3f}s"
            )

            return self._build_response_payload(
                query=query,
                intent=intent,
                confidence=confidence,
                entities={},
                response=redirect_response,
                context_used=False,
                sap_executed=False,
                session_pending=False
            )

        # 3. Pass to Dialog Manager (Slot Filling / Dialog state)
        dialog_start = time.time()
        missing_prompt, action_params = self.dialog_manager.process_dialog_turn(
            session=session,
            intent=intent,
            entities=entities
        )
        dialog_duration = time.time() - dialog_start

        response_text = ""
        context_used = False
        sap_executed = False
        execution_details = {}

        action_start = time.time()
        # 4. If missing details, prompt the user
        if missing_prompt:
            response_text = missing_prompt
            session.add_message(role="assistant", content=response_text)
            self.session_store.save_session(session)
            
            action_duration = time.time() - action_start
            total_duration = time.time() - start_time
            logger.info(
                f"Execution time profile (Slot filling): session_store={session_duration:.3f}s, "
                f"nlp_pipeline={nlp_duration:.3f}s, dialog_manager={dialog_duration:.3f}s, "
                f"action_and_synthesis={action_duration:.3f}s, total={total_duration:.3f}s"
            )
            
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
                
            emp_id = str(action_params.get("employee_id") or "")
            
            logger.info(f"Executing SAP Action: {action_name} for employee: {emp_id}")
            
            try:
                if action_name == "request_leave":
                    leave_res = self.hr_client.request_leave(
                        employee_id=emp_id,
                        leave_type=str(action_params.get("leave_type") or ""),
                        start_date=str(action_params.get("start_date") or ""),
                        end_date=str(action_params.get("end_date") or "")
                    )
                    execution_details = leave_res.model_dump()
                    
                    if self.settings.orchestrator.use_sap_templates:
                        response_text = ResponseTemplates.get_leave_response(
                            request_id=leave_res.request_id,
                            employee_id=emp_id,
                            leave_type=leave_res.leave_type,
                            start_date=leave_res.start_date,
                            end_date=leave_res.end_date,
                            status=leave_res.status,
                            message=leave_res.message
                        )
                    else:
                        # LLM ground response building
                        llm_instruction = PromptRegistry.SAP_REQUEST_LEAVE_USER.format(
                            request_id=leave_res.request_id,
                            employee_id=emp_id,
                            leave_type=leave_res.leave_type,
                            start_date=leave_res.start_date,
                            end_date=leave_res.end_date,
                            status=leave_res.status,
                            message=leave_res.message
                        )
                        response_text = await self.llm_client.query_llm([
                            {"role": "system", "content": PromptRegistry.SAP_SYSTEM},
                            {"role": "user", "content": llm_instruction}
                        ])
                    
                elif action_name == "get_salary_slip":
                    salary_res = self.hr_client.get_salary_slip(
                        employee_id=emp_id,
                        month=str(action_params.get("month") or "")
                    )
                    execution_details = salary_res.model_dump()
                    
                    if self.settings.orchestrator.use_sap_templates:
                        response_text = ResponseTemplates.get_salary_slip_response(
                            employee_id=emp_id,
                            month=salary_res.month,
                            basic_salary=salary_res.basic_salary,
                            housing_allowance=salary_res.housing_allowance,
                            transport_allowance=salary_res.transport_allowance,
                            deductions=salary_res.deductions,
                            net_salary=salary_res.net_salary
                        )
                    else:
                        llm_instruction = PromptRegistry.SAP_GET_SALARY_SLIP_USER.format(
                            employee_id=emp_id,
                            month=salary_res.month,
                            basic_salary=salary_res.basic_salary,
                            housing_allowance=salary_res.housing_allowance,
                            transport_allowance=salary_res.transport_allowance,
                            deductions=salary_res.deductions,
                            net_salary=salary_res.net_salary
                        )
                        response_text = await self.llm_client.query_llm([
                            {"role": "system", "content": PromptRegistry.SAP_SYSTEM},
                            {"role": "user", "content": llm_instruction}
                        ])
                    
                else: # get_profile
                    profile_res = self.hr_client.get_employee_profile(employee_id=emp_id)
                    execution_details = profile_res.model_dump()
                    
                    if self.settings.orchestrator.use_sap_templates:
                        response_text = ResponseTemplates.get_profile_response(
                            first_name=profile_res.first_name,
                            last_name=profile_res.last_name,
                            department=profile_res.department,
                            position=profile_res.position,
                            email=profile_res.email,
                            status=profile_res.status
                        )
                    else:
                        llm_instruction = PromptRegistry.SAP_GET_PROFILE_USER.format(
                            first_name=profile_res.first_name,
                            last_name=profile_res.last_name,
                            department=profile_res.department,
                            position=profile_res.position,
                            email=profile_res.email,
                            status=profile_res.status
                        )
                        response_text = await self.llm_client.query_llm([
                            {"role": "system", "content": PromptRegistry.SAP_SYSTEM},
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
                system_instructions = PromptRegistry.RAG_SYSTEM_TEMPLATE.format(context=context)
                
                # Assemble conversation context including history for better multi-turn interaction
                messages = [{"role": "system", "content": system_instructions}]
                # Append last few messages of history for conversational context (limit to last 3 messages)
                for hist_msg in session.history[-4:-1]:
                    messages.append({"role": hist_msg.role, "content": hist_msg.content})
                messages.append({"role": "user", "content": query})
                
                response_text = await self.llm_client.query_llm(messages)
            else:
                logger.warning("No context found in RAG collection. Falling back to default assistant prompt.")
                messages = [
                    {"role": "system", "content": PromptRegistry.FALLBACK_SYSTEM},
                    {"role": "user", "content": query}
                ]
                response_text = await self.llm_client.query_llm(messages)

        # 7. Update and save session history
        session.add_message(role="assistant", content=response_text)
        self.session_store.save_session(session)
        
        action_duration = time.time() - action_start
        total_duration = time.time() - start_time
        logger.info(
            f"Execution time profile (Success): session_store={session_duration:.3f}s, "
            f"nlp_pipeline={nlp_duration:.3f}s, dialog_manager={dialog_duration:.3f}s, "
            f"action_and_synthesis={action_duration:.3f}s, total={total_duration:.3f}s"
        )

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
