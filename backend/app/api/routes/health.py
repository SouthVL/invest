from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "south-invest-api",
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
