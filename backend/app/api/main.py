from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.demo import router as demo_router
from app.api.routes.health import router as health_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.session import router as session_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="South Invest API",
        version="0.1.0",
        description="Read-only API for South Invest demo and portfolio analytics.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(health_router)
    app.include_router(demo_router, prefix="/api/v1/demo", tags=["demo"])
    app.include_router(session_router, prefix="/api/v1", tags=["session"])
    app.include_router(portfolio_router, prefix="/api/v1", tags=["portfolio"])
    return app


app = create_app()
