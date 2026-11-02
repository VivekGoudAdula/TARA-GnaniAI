"""TARA backend – FastAPI application factory."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, dev


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="TARA – Targeted Acquisition & Reach Agent",
        version="0.1.0",
        description="Voice-first outreach platform built on Gnani AI.",
    )

    # Allow the Vite dev server to call the backend during development.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router, prefix="/api")

    dev_enabled = os.getenv("DEV_ENDPOINTS", "false").lower() == "true"
    if dev_enabled:
        application.include_router(dev.router, prefix="/api/dev")

    return application


app = create_app()

