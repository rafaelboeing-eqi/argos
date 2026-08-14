from fastapi import APIRouter

from app.core.database import check_database_connection
from app.schemas.health import HealthResponse, RootResponse

router = APIRouter()


@router.get("/", response_model=RootResponse)
def read_root() -> RootResponse:
    return RootResponse(system="ARGOS", status="online")


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    database_ok = check_database_connection()
    return HealthResponse(api="ok", database="connected" if database_ok else "disconnected")
