import os
import sys
import time
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Adjust path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from core.logger import get_logger
from core.config_manager import get_settings

logger = get_logger("llm_inference_service")
settings = get_settings()

app = FastAPI(
    title="AskHR Local LLM Inference Service",
    description="Exposes local GGUF models via an OpenAI-compatible API using llama-cpp-python",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for llama model
llama_model = None
mock_mode = False

# OpenAI compatible request/response schemas
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "qwen2.5"
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False

class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str

class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4()}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatChoice]
    usage: UsageInfo

@app.on_event("startup")
def startup_event():
    global llama_model, mock_mode
    
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "models"))
    
    # ── Priority order: prefer non-quantized models that work on CPU with low RAM ──
    # 1. Non-AWQ models first (like Qwen2.5-0.5B-Instruct) — proven to work on CPU
    # 2. AWQ models last — require GPU/CUDA or 16GB+ RAM for float32 dequantization
    CPU_MODEL_PRIORITY = [
        "Qwen2.5-0.5B-Instruct",   # ~2 GB RAM, non-quantized, fast on CPU
        "Qwen2.5-1.5B-Instruct",   # ~6 GB RAM, non-quantized
    ]
    
    AWQ_MODEL_FALLBACK = [
        "Qwen3-4B-AWQ",            # ~16 GB RAM when dequantized to float32
    ]
    
    # ── Try non-quantized CPU-friendly models first (hudhud approach) ──
    for model_name in CPU_MODEL_PRIORITY:
        model_path = os.path.join(models_dir, model_name)
        if not os.path.isdir(model_path):
            continue
        logger.info(f"Found CPU-friendly model: {model_name}. Initializing via Transformers (CPU)...")
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
            
            logger.info("Loading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, use_fast=False)
            
            config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
            # Strip quantization_config if present (safety — non-AWQ models typically don't have one)
            if hasattr(config, "quantization_config"):
                logger.info("Stripping quantization config for CPU loading...")
                delattr(config, "quantization_config")
            
            logger.info(f"Loading model weights as float32 on CPU...")
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                config=config,
                trust_remote_code=True,
                torch_dtype=torch.float32,
                ignore_mismatched_sizes=True
            )
            
            llama_model = (model, tokenizer)
            logger.info(f"Transformers Engine (CPU) Loaded Successfully: {model_name}")
            mock_mode = False
            return
        except Exception as e:
            logger.error(f"Failed to load {model_name} via Transformers: {e}", exc_info=True)
    
    # ── Try AWQ models as fallback (requires significant RAM) ──
    for model_name in AWQ_MODEL_FALLBACK:
        model_path = os.path.join(models_dir, model_name)
        if not os.path.isdir(model_path):
            continue
        logger.warning(
            f"Only AWQ model found: {model_name}. "
            "AWQ requires GPU/CUDA or 16GB+ RAM for CPU dequantization. Attempting anyway..."
        )
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
            
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, use_fast=False)
            config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
            if hasattr(config, "quantization_config"):
                delattr(config, "quantization_config")
            
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                config=config,
                trust_remote_code=True,
                torch_dtype=torch.float32,
                ignore_mismatched_sizes=True
            )
            
            llama_model = (model, tokenizer)
            logger.info(f"Transformers Engine (CPU) Loaded Successfully: {model_name}")
            mock_mode = False
            return
        except Exception as e:
            logger.error(f"Failed to load AWQ model {model_name}: {e}", exc_info=True)

    model_path = os.getenv("LLM_MODEL_PATH", settings.llm.model_path)
    logger.info("Initializing Local LLM Service...", extra_fields={"model_path": model_path})
    
    # Check if model path exists
    if not os.path.exists(model_path):
        logger.error(
            "Model file NOT found. Service will boot in MOCK MODE for local testing.",
            extra_fields={"model_path": model_path}
        )
        logger.info(
            "INSTRUCTIONS: Please place your local Qwen GGUF model in the models/ directory "
            f"or update config.yaml with the correct path. Expected path: {os.path.abspath(model_path)}"
        )
        mock_mode = True
        return
        
    try:
        # Lazy import llama-cpp to allow mock execution even if library isn't fully compiled yet
        import llama_cpp
        
        logger.info("Loading GGUF model into memory...", extra_fields={"model_path": model_path})
        start_time = time.time()
        
        llama_model = llama_cpp.Llama(
            model_path=model_path,
            n_ctx=settings.llm.n_ctx,
            n_threads=settings.llm.n_threads,
            n_gpu_layers=settings.llm.n_gpu_layers,
            verbose=False
        )
        
        duration = time.time() - start_time
        logger.info(
            "GGUF model loaded successfully!", 
            extra_fields={"model_path": model_path, "load_duration_seconds": round(duration, 2)}
        )
    except Exception as e:
        logger.error("Failed to load model via llama-cpp-python. Falling back to MOCK MODE.", exc_info=True)
        mock_mode = True

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible Chat Completions endpoint.
    """
    logger.info("Received chat completion request", extra_fields={"model": request.model, "messages_count": len(request.messages)})
    
    if mock_mode:
        # Fallback simulated response for local testing
        user_query = request.messages[-1].content
        mock_reply = simulate_qwen_response(request.messages)
        
        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=mock_reply),
                    finish_reason="stop"
                )
            ],
            usage=UsageInfo(
                prompt_tokens=len(user_query.split()),
                completion_tokens=len(mock_reply.split()),
                total_tokens=len(user_query.split()) + len(mock_reply.split())
            )
        )
        
    try:
        # Check if loaded via Transformers
        if isinstance(llama_model, tuple):
            model, tokenizer = llama_model
            
            # Use tokenizer's apply_chat_template (like hudhud engine.py)
            # This handles model-specific formatting automatically
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
            formatted_prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            import torch
            inputs = tokenizer(formatted_prompt, return_tensors="pt").to("cpu")
            
            logger.info("Running transformers model CPU inference...")
            start_time = time.time()
            
            temp = request.temperature if request.temperature is not None else settings.llm.temperature
            max_t = request.max_tokens if request.max_tokens is not None else settings.llm.max_tokens
            
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=max_t,
                temperature=temp,
                do_sample=True if temp > 0 else False,
                repetition_penalty=1.1
            )
            
            duration = time.time() - start_time
            response_ids = generated_ids[0][len(inputs.input_ids[0]):]
            response_text = tokenizer.decode(response_ids, skip_special_tokens=True).strip()
            
            logger.info(
                "Transformers inference completed", 
                extra_fields={"duration_seconds": round(duration, 2), "response_length": len(response_text)}
            )
            
            return ChatCompletionResponse(
                model=request.model,
                choices=[
                    ChatChoice(
                        index=0,
                        message=ChatMessage(role="assistant", content=response_text),
                        finish_reason="stop"
                    )
                ],
                usage=UsageInfo(
                    prompt_tokens=len(inputs.input_ids[0]),
                    completion_tokens=len(response_ids),
                    total_tokens=len(inputs.input_ids[0]) + len(response_ids)
                )
            )

        # Convert request messages to llama-cpp format
        formatted_prompt = ""
        for msg in request.messages:
            formatted_prompt += f"<|im_start|>{msg.role}\n{msg.content}<|im_end|>\n"
        formatted_prompt += "<|im_start|>assistant\n"
        
        # Run inference
        temp = request.temperature if request.temperature is not None else settings.llm.temperature
        max_t = request.max_tokens if request.max_tokens is not None else settings.llm.max_tokens
        
        logger.info("Running llama-cpp inference local execution...")
        start_time = time.time()
        
        output = llama_model(
            formatted_prompt,
            max_tokens=max_t,
            temperature=temp,
            stop=["<|im_end|>", "<|im_start|>"],
            echo=False
        )
        
        duration = time.time() - start_time
        response_text = output["choices"][0]["text"].strip()
        
        logger.info(
            "Inference completed", 
            extra_fields={"duration_seconds": round(duration, 2), "response_length": len(response_text)}
        )
        
        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_text),
                    finish_reason="stop"
                )
            ],
            usage=UsageInfo(
                prompt_tokens=output["usage"]["prompt_tokens"],
                completion_tokens=output["usage"]["completion_tokens"],
                total_tokens=output["usage"]["total_tokens"]
            )
        )
        
    except Exception as e:
        logger.error("Error during llama-cpp inference", exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM Inference Error: {str(e)}")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "mock_mode": mock_mode,
        "model_loaded": llama_model is not None,
        "engine": "llama-cpp-python"
    }

def simulate_qwen_response(messages: List[ChatMessage]) -> str:
    """
    Generates intelligent simulated response matching the style of Qwen 2.5
    when the local GGUF model is not yet placed in the models folder.
    This version dynamically checks for system message RAG contexts or SAP instructions.
    """
    system_msg = next((m.content for m in messages if m.role == "system"), "")
    user_msg = messages[-1].content if messages else ""
    
    logger.info(f"MOCK LLM: system_msg_len={len(system_msg)}, user_msg_len={len(user_msg)}")
    
    # 0. Check if this is an NLP parser request (expects a valid JSON response)
    if "expert NLP parser" in system_msg or "valid JSON object matching this schema" in system_msg:
        import re
        import json
        actual_query = user_msg.replace("Query:", "").strip()
        q = actual_query.lower()
        
        intent = "RAG"
        confidence = 0.9
        employee_id = None
        leave_type = None
        start_date = None
        end_date = None
        month = None
        
        # Rule-based intent detection
        if any(kw in q for kw in ["تقديم", "طلب", "اجازه", "سجل", "احضر", "كشف", "الراتب", "payslip", "leave", "vacation"]):
            if any(kw in q for kw in ["سياسه", "بدل", "حقوق", "كم يوم", "كم يستحق", "policy", "benefit"]):
                intent = "RAG"
            else:
                intent = "SAP"
        
        # Extract employee_id
        emp_match = re.search(r"emp\d+", q)
        if emp_match:
            employee_id = emp_match.group(0).upper()
            
        # Extract leave_type
        if "سنويه" in q or "سنوية" in q or "annual" in q:
            leave_type = "ANNUAL_LEAVE"
        elif "مرضيه" in q or "مرضية" in q or "sick" in q:
            leave_type = "SICK_LEAVE"
        elif "وضع" in q or "امومه" in q or "maternity" in q:
            leave_type = "MATERNITY_LEAVE"
            
        # Extract dates (YYYY-MM-DD)
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", q)
        if len(dates) >= 2:
            start_date = dates[0]
            end_date = dates[1]
        elif len(dates) == 1:
            start_date = dates[0]
            
        # Extract month
        for m in ["مايو", "may", "يونيو", "june", "ابريل", "april"]:
            if m in q:
                month = m.capitalize()
                
        nlp_json = {
            "intent": intent,
            "confidence": confidence,
            "entities": {
                "employee_id": employee_id,
                "leave_type": leave_type,
                "start_date": start_date,
                "end_date": end_date,
                "month": month
            }
        }
        return json.dumps(nlp_json, ensure_ascii=False)
    
    # 1. Check if it's an SAP leave request confirmation instruction
    if "تقديم طلب الإجازة في نظام SAP" in user_msg or "طلب الإجازة في نظام SAP" in user_msg:
        lines = user_msg.split('\n')
        req_id = "LR-XXXX"
        emp_id = ""
        leave_type = ""
        period = ""
        for line in lines:
            if "رقم الطلب:" in line:
                req_id = line.split(":", 1)[1].strip()
            elif "الرقم الوظيفي للموظف:" in line:
                emp_id = line.split(":", 1)[1].strip()
            elif "نوع الإجازة:" in line:
                leave_type = line.split(":", 1)[1].strip()
            elif "الفترة:" in line:
                period = line.split(":", 1)[1].strip()
                
        leave_type_ar = "السنوية" if "ANNUAL" in leave_type.upper() else leave_type
        return (
            "[Simulated Qwen-2.5 Response - Mock Mode]\n"
            f"تم تقديم طلب إجازتك {leave_type_ar} بنجاح للموظف {emp_id} "
            f"للفترة {period}. رقم طلبك في نظام SAP هو: {req_id}."
        )

    # 2. Check if it's an SAP payslip retrieval instruction
    if "تفاصيل كشف الراتب (Payslip)" in user_msg:
        lines = user_msg.split('\n')
        emp_id = ""
        month = ""
        basic = ""
        housing = ""
        transport = ""
        deductions = ""
        net = ""
        for line in lines:
            if "للموظف" in line:
                emp_id = line.split("للموظف", 1)[1].split("عن شهر", 1)[0].strip()
                month = line.split("عن شهر", 1)[1].replace(":", "").strip()
            if "الراتب الأساسي:" in line:
                basic = line.split(":", 1)[1].strip()
            elif "بدل السكن:" in line:
                housing = line.split(":", 1)[1].strip()
            elif "بدل المواصلات:" in line:
                transport = line.split(":", 1)[1].strip()
            elif "الاستقطاعات:" in line:
                deductions = line.split(":", 1)[1].strip()
            elif "صافي الراتب:" in line:
                net = line.split(":", 1)[1].strip()
                
        return (
            "[Simulated Qwen-2.5 Response - Mock Mode]\n"
            f"تم استرجاع كشف الراتب للموظف {emp_id} عن شهر {month} بنجاح:\n"
            f"- الراتب الأساسي: {basic}\n"
            f"- بدل السكن: {housing}\n"
            f"- بدل المواصلات: {transport}\n"
            f"- الاستقطاعات: {deductions}\n"
            f"- صافي الراتب النهائي: {net}"
        )

    # 3. Check if it's an SAP employee profile retrieval instruction
    if "ملف الموظف المسترجع من SAP" in user_msg:
        lines = user_msg.split('\n')
        name = ""
        dept = ""
        position = ""
        for line in lines:
            if "الاسم:" in line:
                name = line.split(":", 1)[1].strip()
            elif "الإدارة:" in line:
                dept = line.split(":", 1)[1].strip()
            elif "المسمى الوظيفي:" in line:
                position = line.split(":", 1)[1].strip()
        return (
            "[Simulated Qwen-2.5 Response - Mock Mode]\n"
            f"مرحباً بك {name}. لقد تم استرداد ملفك الوظيفي من نظام SAP SuccessFactors بنجاح:\n"
            f"- الإدارة: {dept}\n"
            f"- المسمى الوظيفي: {position}\n"
            "كيف يمكنني مساعدتك اليوم؟"
        )

    # 4. Check for RAG context
    if "السياق المسترجع من اللوائح والسياسات الرسمية" in system_msg:
        context_parts = system_msg.split("=========================================")
        if len(context_parts) >= 3:
            actual_context = context_parts[1].strip()
            
            q = user_msg.lower()
            lines = actual_context.split('\n')
            
            if "سنوية" in q or "annual" in q or "vacation" in q:
                matched_lines = [l for l in lines if "سنوية" in l or "30" in l or "ترحيل" in l]
                if matched_lines:
                    bullets = "\n".join([f"- {l.strip().lstrip('- ').strip()}" for l in matched_lines[:4] if l.strip()])
                    return (
                        "[Simulated Qwen-2.5 Response - Mock Mode]\n"
                        "بناءً على السياسة الرسمية للإجازات في مجموعة HSA Group:\n"
                        f"{bullets}"
                    )
            elif "مرضية" in q or "sick" in q:
                matched_lines = [l for l in lines if "مرضية" in l or "15" in l]
                if matched_lines:
                    bullets = "\n".join([f"- {l.strip().lstrip('- ').strip()}" for l in matched_lines[:4] if l.strip()])
                    return (
                        "[Simulated Qwen-2.5 Response - Mock Mode]\n"
                        "تنص سياسة الإجازات المرضية لمجموعة HSA Group على ما يلي:\n"
                        f"{bullets}"
                    )
            elif "سكن" in q or "housing" in q:
                matched_lines = [l for l in lines if "سكن" in l or "25%" in l]
                if matched_lines:
                    bullets = "\n".join([f"- {l.strip().lstrip('- ').strip()}" for l in matched_lines[:4] if l.strip()])
                    return (
                        "[Simulated Qwen-2.5 Response - Mock Mode]\n"
                        "تفاصيل بدل السكن وفقاً لسياسات مجموعة HSA Group:\n"
                        f"{bullets}"
                    )
            elif "تأمين" in q or "medical" in q or "insurance" in q:
                matched_lines = [l for l in lines if "تأمين" in l or "طبي" in l or "Class A" in l]
                if matched_lines:
                    bullets = "\n".join([f"- {l.strip().lstrip('- ').strip()}" for l in matched_lines[:4] if l.strip()])
                    return (
                        "[Simulated Qwen-2.5 Response - Mock Mode]\n"
                        "تغطية التأمين الطبي بمجموعة HSA Group تشمل:\n"
                        f"{bullets}"
                    )
            elif "مواصلات" in q or "transport" in q:
                matched_lines = [l for l in lines if "مواصلات" in l or "سيارة" in l or "150" in l or "300" in l]
                if matched_lines:
                    bullets = "\n".join([f"- {l.strip().lstrip('- ').strip()}" for l in matched_lines[:4] if l.strip()])
                    return (
                        "[Simulated Qwen-2.5 Response - Mock Mode]\n"
                        "بدل المواصلات المعتمد في مجموعة HSA Group هو:\n"
                        f"{bullets}"
                    )
            
            # Default fallback with context preview
            return (
                "[Simulated Qwen-2.5 Response - Mock Mode]\n"
                f"أهلاً بك. استناداً إلى لوائح الموارد البشرية لمجموعة HSA:\n"
                f"{actual_context[:350]}..."
            )
            
    # 5. Standard general queries fallback
    q = user_msg.lower()
    if "إجازة" in q or "leave" in q or "vacation" in q:
        return (
            "[Simulated Qwen-2.5 Response - Mock Mode]\n"
            "مرحباً بك! بخصوص طلب الإجازة، يرجى تزويدي بنوع الإجازة (مثل: إجازة سنوية، مرضية، بدون راتب) "
            "والتاريخ المطلوب للبدء والانتهاء. يمكنني مساعدتك في استخراج هذه البيانات وإرسالها لنظام SAP."
        )
    elif "راتب" in q or "salary" in q or "slip" in q:
        return (
            "[Simulated Qwen-2.5 Response - Mock Mode]\n"
            "أهلاً بك. للحصول على تفاصيل كشف الراتب (Payslip)، يرجى تزويدي بالرقم الوظيفي الخاص بك والمسجل في SAP "
            "والشهر المستهدف (مثال: مايو 2026)."
        )
    elif "policy" in q or "سياسة" in q or "حقوق" in q or "بدل" in q:
        return (
            "[Simulated Qwen-2.5 Response - Mock Mode]\n"
            "بناءً على سياسات الموارد البشرية لمجموعة HSA:\n"
            "- يحق للموظف إجازة سنوية مدتها 30 يوماً مدفوعة الأجر بالكامل بعد إتمام عام من الخدمة.\n"
            "- يتم تقديم بدل السكن شهرياً بنسبة 25% من الراتب الأساسي طبقاً للدرجة الوظيفية."
        )
    else:
        return (
            "[Simulated Qwen-2.5 Response - Mock Mode]\n"
            f"مرحباً بك في نظام AskHR. لقد استقبلت استفسارك: '{user_msg}'.\n"
            "أنا جاهز لمساعدتك في الاستفسار عن سياسات الموارد البشرية لمجموعة HSA أو تنفيذ الإجراءات عبر نظام SAP."
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=os.getenv("LLM_SERVICE_HOST", settings.llm.service_host),
        port=int(os.getenv("LLM_SERVICE_PORT", settings.llm.service_port)),
        reload=True
    )
