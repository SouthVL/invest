from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.application.macro_indicators import CachedCurrentMacroIndicatorsProvider, MacroIndicatorsStrictError, build_current_macro_snapshot
from app.integrations.cbr.current_indicators import CbrCurrentIndicatorsProvider
from app.reporting.serializers.macro_json import macro_snapshot_to_dict
from app.storage.macro_indicators import MacroIndicatorsRepository

router = APIRouter()


@router.get("/macro")
@router.get("/macro/current")
def current_macro(strict: bool = False) -> dict[str, Any]:
    try:
        snapshot = build_current_macro_snapshot(default_macro_provider(), strict=strict)
    except MacroIndicatorsStrictError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Current macro indicators are incomplete.",
        ) from exc
    return macro_snapshot_to_dict(snapshot)


def default_macro_provider() -> CachedCurrentMacroIndicatorsProvider:
    return CachedCurrentMacroIndicatorsProvider(
        upstream=CbrCurrentIndicatorsProvider(),
        repository=MacroIndicatorsRepository(macro_db_path()),
    )


def macro_db_path() -> Path:
    return Path(os.environ.get("SOUTH_INVEST_DB_PATH", "invest.db"))
