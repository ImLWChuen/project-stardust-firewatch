from pydantic import BaseModel

class AOICreate(BaseModel):
    """Request schema for creating a new area of interest."""

    name: str
    country: str

class AOIResponse(BaseModel):
    """Response schema for an area of interest."""

    id: str
    name: str
    country: str
