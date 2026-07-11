"""Sovereign — Banking Annual Report Intelligence Platform (API entrypoint).

Run:  uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.seeds.demo import seed_demo
from app.seeds.roster import seed_indian_roster


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        # Indian scheduled-commercial-bank roster (institutions only) always
        # seeds; synthetic demo figures only when enabled.
        seed_indian_roster(db)
        if settings.seed_demo_data:
            seed_demo(db)
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    """Optional shared-secret gate (SOVEREIGN_API_KEY). A stopgap for demo
    deployments — production requires SSO/OIDC with role-based access."""
    if settings.api_key and request.url.path.startswith("/api"):
        if request.headers.get("X-API-Key") != settings.api_key:
            return JSONResponse({"detail": "Invalid or missing API key"}, status_code=401)
    return await call_next(request)


app.include_router(router)
