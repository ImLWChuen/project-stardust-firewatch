from pydantic import BaseModel

class HarmonizationStatusResponse(BaseModel):
    status: str
    model_version: str
