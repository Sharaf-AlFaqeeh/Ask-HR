import os
import sys
import uuid
import asyncio
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Adjust path to import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from core.logger import get_logger, set_correlation_id, clear_correlation_id
from core.config_manager import get_settings
from core.exceptions import AskHRException
from core.security.tenant import clear_tenant_id
from services.orchestrator_service.di.container import get_container

logger = get_logger("orchestrator_main")
settings = get_settings()

app = FastAPI(
    title="AskHR Enterprise AI Orchestrator",
    description="Enterprise-Grade FastAPI clean architecture orchestrator integrating local Qwen RAG & SAP SuccessFactors",
    version="1.1.0"
)

# Enable CORS for frontend/call center integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for request tracing, correlation IDs, and tenant isolation clearing
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    # Retrieve trace ID from header or generate a new one
    trace_id = request.headers.get("X-Correlation-ID", uuid.uuid4().hex[:12])
    set_correlation_id(trace_id)
    
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = trace_id
        return response
    finally:
        # Guarantee cleaning thread-local context variables to prevent leakage
        clear_correlation_id()
        clear_tenant_id()

async def periodic_services_health_check():
    """
    Checks the health of the LLM Inference Service and Qdrant DB periodically
    to ensure resilient auto-recovery.
    """
    await asyncio.sleep(5) # Delay initial check to let other services boot
    
    llm_url = settings.orchestrator.llm_api_url
    if "/v1" in llm_url:
        llm_url = llm_url.replace("/v1", "")
    llm_url = f"{llm_url.rstrip('/')}/health"
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            # 1. Check LLM Service
            try:
                response = await client.get(llm_url)
                if response.status_code == 200:
                    logger.info(f"Resilient Health Check: LLM Inference Service is ONLINE at {llm_url}")
                else:
                    logger.warning(f"Resilient Health Check: LLM Inference Service at {llm_url} returned code {response.status_code}")
            except Exception as e:
                logger.warning(f"Resilient Health Check: LLM Inference Service is OFFLINE at {llm_url}. Details: {e}")
                
            # 2. Check Qdrant Connection
            try:
                container = get_container()
                if container.retriever.client is None:
                    logger.info("Resilient Health Check: Qdrant Client is offline. Attempting auto-reconnection...")
                    container.retriever.init_client()
                else:
                    # Test connection by listing collections (lightweight call)
                    container.retriever.client.get_collections()
                    logger.info("Resilient Health Check: Qdrant DB is ONLINE and connected.")
            except Exception as e:
                logger.warning(f"Resilient Health Check: Qdrant DB is OFFLINE or reconnection failed: {e}")
                # Reset client to None to trigger reconnection on next cycle
                try:
                    container = get_container()
                    container.retriever.client = None
                except Exception:
                    pass
                
            await asyncio.sleep(15) # Check every 15 seconds

# pyrefly: ignore [deprecated]
@app.on_event("startup")
async def startup_event():
    # Force DI Container initialization on boot
    get_container()
    logger.info("AskHR Orchestrator service started successfully.")
    # Start periodic services health checker in background
    asyncio.create_task(periodic_services_health_check())

# pyrefly: ignore [deprecated]
@app.on_event("shutdown")
async def shutdown_event():
    # Retrieve container and trigger clean resource shutdown
    container = get_container()
    if hasattr(container.llm_client, "close"):
        await container.llm_client.close()
    logger.info("AskHR Orchestrator service shut down successfully.")

from fastapi.staticfiles import StaticFiles

# Register API Routers
from services.orchestrator_service.api.v1.chat import router as chat_router
from services.orchestrator_service.api.v1.admin import router as admin_router

app.include_router(chat_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

# Mount HSA policies folder to serve PDF files
hsa_policies_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../vector_db_service/HSA_policies"))
if os.path.exists(hsa_policies_dir):
    app.mount("/policies-files", StaticFiles(directory=hsa_policies_dir), name="policies-files")
    logger.info(f"Mounted policies directory at {hsa_policies_dir}")
else:
    logger.warning(f"Policies directory not found at {hsa_policies_dir}")

@app.get("/")
def read_root():
    return {"status": "running", "service": "AskHR AI Orchestrator"}

# Enterprise Global Exception Handler
@app.exception_handler(AskHRException)
async def askhr_exception_handler(request: Request, exc: AskHRException):
    """
    Catches custom application errors and structures them safely for the response payload.
    """
    logger.error(
        f"Application Error: {exc.message}",
        extra_fields={"status_code": exc.status_code, "details": exc.details}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.message,
                "type": exc.__class__.__name__,
                "details": exc.details
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler to avoid leaking traceback details in production responses.
    """
    logger.error("Unhandled System Exception caught", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "message": "An unexpected system error occurred. Please try again later.",
                "type": "InternalServerError",
                "details": {}
            }
        }
    )

@app.get("/health")
def health_check():
    container = get_container()
    return {
        "status": "healthy",
        "service": "AskHR AI Orchestrator",
        "env": settings.app.env,
        "sap_mock_mode": settings.sap.mock_mode,
        "qdrant_db_connected": container.retriever.client is not None
    }

if __name__ == "__main__":
    import uvicorn
    # Start orchestrator
    uvicorn.run(
        "main:app",
        host=os.getenv("ORCHESTRATOR_HOST", settings.orchestrator.host),
        port=int(os.getenv("ORCHESTRATOR_PORT", settings.orchestrator.port)),
        reload=True
    )
