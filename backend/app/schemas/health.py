from pydantic import BaseModel


class RootResponse(BaseModel):
    system: str
    status: str


class HealthResponse(BaseModel):
    api: str
    database: str
