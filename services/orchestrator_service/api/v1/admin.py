import sys
import os
from fastapi import APIRouter, Depends, HTTPException
from core.security.auth import require_role, UserPrincipal
from services.orchestrator_service.di.container import get_container
from core.logger import get_logger

logger = get_logger("admin_api")
router = APIRouter(prefix="/v1/admin", tags=["admin"])

@router.delete("/sessions/{session_id}")
def clear_session(
    session_id: str, 
    admin: UserPrincipal = Depends(require_role("hr_admin"))
):
    """
    Clears conversation session history and state. Restricted to HR admins.
    """
    logger.info(f"Admin requested clearing session: {session_id} (Admin ID: {admin.employee_id})")
    container = get_container()
    deleted = container.session_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": f"Session '{session_id}' cleared successfully."}

@router.post("/ingest")
def trigger_ingestion(
    admin: UserPrincipal = Depends(require_role("hr_admin"))
):
    """
    Triggers RAG policies document chunking and indexing in Qdrant. Restricted to HR admins.
    """
    logger.info(f"Admin triggered document ingestion (Admin ID: {admin.employee_id})")
    
    # Dynamically import and run data ingestion to avoid circular dependency
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
    from services.vector_db_service.data_ingestion import ingest_documents
    
    try:
        ingest_documents()
        # Re-initialize the Qdrant retriever in DI container to read the new collection
        container = get_container()
        container.retriever._init_client()
        return {"success": True, "message": "Document ingestion completed and retriever re-loaded."}
    except Exception as e:
        logger.error("Admin ingestion trigger failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
