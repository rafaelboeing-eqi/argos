from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import companies, credit_analyses, market, sectors, system
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="ARGOS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(market.router)
app.include_router(companies.router)
app.include_router(credit_analyses.router)
app.include_router(sectors.router)
