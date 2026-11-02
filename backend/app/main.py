"""TARA backend – FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import close_db, init_db
from app.routers import (
    auth, campaigns, campaign_ops, communication, dev, governance,
    health, importer, products, scoring, voice
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle tasks."""
    try:
        await init_db()
    except Exception:
        pass
    yield
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="TARA – Targeted Acquisition & Reach Agent",
        version="0.3.0",
        description="Voice-first outreach platform built on Gnani AI.",
        lifespan=lifespan,
    )

    # Allow Vite dev server to call backend during development
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix="/api")
    application.include_router(auth.router)
    application.include_router(products.router)
    application.include_router(importer.router)
    application.include_router(scoring.router)
    application.include_router(campaigns.router)
    application.include_router(campaign_ops.router)
    application.include_router(communication.router)
    application.include_router(governance.router)
    application.include_router(voice.router)

    dev_enabled = os.getenv("DEV_ENDPOINTS", "false").lower() == "true"
    if dev_enabled:
        application.include_router(dev.router, prefix="/api/dev")

    return application


app = create_app()
