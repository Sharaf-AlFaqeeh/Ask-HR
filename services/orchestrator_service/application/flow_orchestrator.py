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
from core.security.tenant import set_tenant_id

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
        # Set tenant ID in context variable for downstream database/API adapters
        set_tenant_id(tenant_id)
        
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

        # 2.5. Intercept SAP actions in production — system cannot process transactional requests yet.
        #      Redirect the user to contact HR directly via phone.
        #      In mock mode (development), we allow the full multi-turn dialog flow for demonstration.
        if intent == "SAP" and not self.settings.sap.mock_mode:
            redirect_response = (
                "مرحباً 👋\n\n"
                "حالياً لا يمكنني تنفيذ هذا الإجراء من خلال النظام.\n"
                "لتقديم طلب إجازة أو أي إجراء آخر، يرجى التواصل مع مركز الخدمة للموارد البشرية على الرقم التالي:\n\n"
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
                entities=entities,
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
            logger.info("SAP action missing fields. Retrieving RAG context to provide helpful policy info...")
            citations = self.retriever.retrieve_context_with_metadata(query)
            
            if citations:
                context_blocks = []
                for cit in citations:
                    source = cit["source"]
                    page_num = cit.get("page_number")
                    if page_num:
                        context_blocks.append(f"[مصدر: {source} (صفحة {page_num})]\n{cit['text']}")
                    else:
                        context_blocks.append(f"[مصدر: {source}]\n{cit['text']}")
                context = "\n\n---\n\n".join(context_blocks)
                
                system_instruction = (
                    "أنت خبير الموارد البشرية لمجموعة هائل سعيد أنعم (HSA Group).\n"
                    "تلقى المستخدم طلباً لمعاملة إدارية في نظام الموارد البشرية، وهناك بعض البيانات الناقصة المطلوبة لإتمامه.\n"
                    "باستخدام معلومات السياسات المرفقة أدناه، قدم للمستخدم إجابة مفيدة تشرح فيها القواعد والشروط الخاصة بالسياسة ذات الصلة بوضوح مع الاستشهاد بذكر اسم المستند والصفحة كمرجع.\n"
                    "ثم في نهاية ردك، اطلب من المستخدم بلطف تزويدك بالبيانات الناقصة المطلوبة لإتمام إجراء المعاملة التجريبية.\n\n"
                    f"البيانات الناقصة المطلوب طلبها من المستخدم:\n{missing_prompt}\n\n"
                    "سياق سياسات الموارد البشرية المسترجعة:\n"
                    "=========================================\n"
                    f"{context}\n"
                    "=========================================\n"
                )
                
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": query}
                ]
                
                logger.info("Invoking LLM to synthesize informative slot-filling prompt...")
                response_text = await self.llm_client.query_llm(messages)
                context_used = True
            else:
                system_instruction = (
                    "أنت خبير الموارد البشرية لمجموعة هائل سعيد أنعم (HSA Group).\n"
                    "تلقى المستخدم طلباً لمعاملة إدارية وهناك بيانات ناقصة.\n"
                    "قم بصياغة طلب البيانات الناقصة التالي بأسلوب حواري مهني وودود للغاية باللغة العربية الفصحى:\n"
                    f"{missing_prompt}"
                )
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": query}
                ]
                response_text = await self.llm_client.query_llm(messages)
                context_used = False

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
                session_pending=True,
                execution_details={"citations": citations} if citations else {}
            )

        # 5. If SAP Action is fully qualified, execute it or prompt for confirmation!
        if action_params:
            action_name = session.pending_action.action_name if session.pending_action else "get_profile"
            if "leave_type" in action_params and "start_date" in action_params:
                action_name = "request_leave"
            elif "month" in action_params:
                action_name = "get_salary_slip"
                
            emp_id = str(action_params.get("employee_id") or "")
            
            logger.info(f"Routing SAP Action: {action_name} for employee: {emp_id}")
            
            # Lookup in registry
            from services.orchestrator_service.actions.registry import get_action_registry
            from services.orchestrator_service.actions.base import ActionType
            
            registry = get_action_registry()
            action = registry.get(action_name)
            
            if action:
                # Run validation
                is_valid, err_msg = action.validate(action_params)
                if not is_valid:
                    response_text = f"⚠️ {err_msg}"
                    session.add_message(role="assistant", content=response_text)
                    self.session_store.save_session(session)
                    return self._build_response_payload(
                        query=query,
                        intent=intent,
                        confidence=confidence,
                        entities=entities,
                        response=response_text,
                        context_used=False,
                        sap_executed=False,
                        session_pending=True
                    )
                
                # Check action type
                if action.action_type == ActionType.TRANSACTIONAL:
                    # Transactional (e.g. Request Leave) requires UI confirmation card
                    action_payload = action.get_ui_template(action_params)
                    response_text = (
                        f"لقد قمت بتجهيز طلب {action.name_ar} الخاص بك.\n"
                        f"يرجى مراجعة وتأكيد البيانات المعروضة في البطاقة أدناه للموافقة على الإرسال والتنفيذ في نظام SAP."
                    )
                    # Keep pending action in session so that it remains active
                    from services.orchestrator_service.domain.models import PendingAction
                    if not session.pending_action:
                        session.pending_action = PendingAction(action_name=action_name)
                    session.pending_action.parameters = action_params
                    session.add_message(role="assistant", content=response_text)
                    self.session_store.save_session(session)
                    
                    return self._build_response_payload(
                        query=query,
                        intent=intent,
                        confidence=confidence,
                        entities=entities,
                        response=response_text,
                        context_used=False,
                        sap_executed=False,
                        session_pending=True,
                        execution_details={"citations": []},
                        action_payload=action_payload
                    )
                else:
                    # Inquiry (e.g. Salary Slip) -> Execute immediately, return data + action UI loading template
                    sap_executed = True
                    action_payload = action.get_ui_template(action_params)
                    
                    try:
                        exec_res = action.execute(emp_id, action_params)
                        execution_details = exec_res
                        
                        if action_name == "get_salary_slip":
                            if self.settings.orchestrator.use_sap_templates:
                                response_text = ResponseTemplates.get_salary_slip_response(
                                    employee_id=emp_id,
                                    month=exec_res.get("month", ""),
                                    basic_salary=exec_res.get("basic_salary", 0.0),
                                    housing_allowance=exec_res.get("housing_allowance", 0.0),
                                    transport_allowance=exec_res.get("transport_allowance", 0.0),
                                    deductions=exec_res.get("deductions", 0.0),
                                    net_salary=exec_res.get("net_salary", 0.0)
                                )
                            else:
                                llm_instruction = PromptRegistry.SAP_GET_SALARY_SLIP_USER.format(
                                    employee_id=emp_id,
                                    month=exec_res.get("month", ""),
                                    basic_salary=exec_res.get("basic_salary", 0.0),
                                    housing_allowance=exec_res.get("housing_allowance", 0.0),
                                    transport_allowance=exec_res.get("transport_allowance", 0.0),
                                    deductions=exec_res.get("deductions", 0.0),
                                    net_salary=exec_res.get("net_salary", 0.0)
                                )
                                response_text = await self.llm_client.query_llm([
                                    {"role": "system", "content": PromptRegistry.SAP_SYSTEM},
                                    {"role": "user", "content": llm_instruction}
                                ])
                        else:
                            response_text = f"تفاصيل الاستعلام الخاصة بك: {exec_res}"
                        
                        # Clear pending action since it's fully resolved
                        session.pending_action = None
                        session.add_message(role="assistant", content=response_text)
                        self.session_store.save_session(session)
                        
                        return self._build_response_payload(
                            query=query,
                            intent=intent,
                            confidence=confidence,
                            entities=entities,
                            response=response_text,
                            context_used=False,
                            sap_executed=True,
                            session_pending=False,
                            execution_details=execution_details,
                            action_payload=action_payload
                        )
                        
                    except Exception as ex:
                        logger.error(f"Error executing SAP action {action_name}: {ex}", exc_info=True)
                        response_text = f"عذراً، فشل جلب البيانات من نظام SAP: {str(ex)}"
                        session.pending_action = None
                        session.add_message(role="assistant", content=response_text)
                        self.session_store.save_session(session)
                        return self._build_response_payload(
                            query=query,
                            intent=intent,
                            confidence=confidence,
                            entities=entities,
                            response=response_text,
                            context_used=False,
                            sap_executed=False,
                            session_pending=False
                        )
            else:
                # Fallback if action is not in registry
                response_text = f"عذراً، الإجراء {action_name} غير مدعوم في النظام حالياً."
                session.pending_action = None
                session.add_message(role="assistant", content=response_text)
                self.session_store.save_session(session)
                return self._build_response_payload(
                    query=query,
                    intent=intent,
                    confidence=confidence,
                    entities=entities,
                    response=response_text,
                    context_used=False,
                    sap_executed=False,
                    session_pending=False
                )

        # 6. RAG Pipeline execution (General Policies)
        else:
            logger.info("Running RAG context retrieval...")
            citations = self.retriever.retrieve_context_with_metadata(query)
            
            if citations:
                context_used = True
                
                # Format context text for the LLM
                context_blocks = []
                for cit in citations:
                    source = cit["source"]
                    page_num = cit.get("page_number")
                    if page_num:
                        context_blocks.append(f"[مصدر: {source} (صفحة {page_num})]\n{cit['text']}")
                    else:
                        context_blocks.append(f"[مصدر: {source}]\n{cit['text']}")
                context = "\n\n---\n\n".join(context_blocks)
                
                system_instructions = PromptRegistry.RAG_SYSTEM_TEMPLATE.format(context=context)
                
                # Assemble conversation context including history for better multi-turn interaction
                messages = [{"role": "system", "content": system_instructions}]
                # Append last few messages of history for conversational context (limit to last 3 messages)
                for hist_msg in session.history[-4:-1]:
                    messages.append({"role": hist_msg.role, "content": hist_msg.content})
                messages.append({"role": "user", "content": query})
                
                response_text = await self.llm_client.query_llm(messages)
                execution_details = {"citations": citations}
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
        execution_details: Optional[Dict[str, Any]] = None,
        action_payload: Optional[Dict[str, Any]] = None
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
            "execution_details": execution_details or {},
            "action_payload": action_payload
        }
