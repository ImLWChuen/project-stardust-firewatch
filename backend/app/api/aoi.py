from fastapi import APIRouter
from app.schemas.aoi import AOICreate, AOIResponse

router = APIRouter()

@router.get("/", response_model=list[AOIResponse])
def list_aois():
    """Return all registered areas of interest."""
    return [{"id": "aoi-1", "name": "Kedah Agricultural Basin", "country": "Malaysia"}]

@router.post("/", response_model=AOIResponse)
def create_aoi(payload: AOICreate):
    """Create a new area of interest from the given payload."""
    return {"id": "aoi-new", "name": payload.name, "country": payload.country}
