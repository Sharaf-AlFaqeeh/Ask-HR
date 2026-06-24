import os
import sys
import uuid
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

# pyrefly: ignore [deprecated]
@app.on_event("startup")
def startup_event():
    # Force DI Container initialization on boot
    get_container()
    logger.info("AskHR Orchestrator service started successfully.")

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
