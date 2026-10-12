from pydantic import BaseModel

class HarmonizationStatusResponse(BaseModel):
    """Response schema for harmonization pipeline status."""

    status: str
    model_version: str
