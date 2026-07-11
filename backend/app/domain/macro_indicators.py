from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

DataQualityStatus = Literal["actual", "cached", "stale", "unavailable"]


class KeyRateValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    value_percent: Decimal
    effective_date: date
    effective_from: date | None = None
    source: str
    source_url: str
    fetched_at: datetime
    quality_status: DataQualityStatus


class RuoniaValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    value_percent: Decimal
    rate_date: date
    publication_date: date
    volume_rub_billion: Decimal | None = None
    trades_count: int | None = None
    participants_count: int | None = None
    calculation_status: str | None = None
    source: str
    source_url: str
    fetched_at: datetime
    quality_status: DataQualityStatus


class AnnualInflationValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    value_percent_yoy: Decimal
    period_year: int
    period_month: int
    target_percent: Decimal | None = None
    source: str
    source_url: str
    fetched_at: datetime
    quality_status: DataQualityStatus


class CurrentMacroSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    report_type: str = "current_macro_indicators"
    generated_at: datetime
    key_rate: KeyRateValue | None = None
    ruonia: RuoniaValue | None = None
    annual_inflation: AnnualInflationValue | None = None
    warnings: list[str]

