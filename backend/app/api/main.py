from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.demo import router as demo_router
from app.api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="South Invest API",
        version="0.1.0",
        description="Read-only API for South Invest demo and portfolio analytics.",
    )
    app.include_router(health_router)
    app.include_router(demo_router, prefix="/api/v1/demo", tags=["demo"])
    return app


app = create_app()
