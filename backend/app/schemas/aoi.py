from pydantic import BaseModel

class AOICreate(BaseModel):
    name: str
    country: str

class AOIResponse(BaseModel):
    id: str
    name: str
    country: str
