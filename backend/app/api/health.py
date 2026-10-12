from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    """Return a simple liveness status for the API service."""
    return {"status": "ok", "service": "Project Stardust API"}
