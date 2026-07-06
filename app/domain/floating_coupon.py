from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FloatingRateIndex(StrEnum):
    KEY_RATE = "key_rate"
    RUONIA = "ruonia"
    MOSPRIME = "mosprime"
    INFLATION = "inflation"
    UNKNOWN = "unknown"


class CouponForecastSource(StrEnum):
    ACTUAL = "actual"
    FORECAST = "forecast"
    UNKNOWN = "unknown"


class VersionedStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class FormulaDataQuality(StrEnum):
    VERIFIED = "verified"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"
    MANUAL = "manual"


class DataSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    url: str | None = None


class FloatingCouponFormula(BaseModel):
    model_config = ConfigDict(frozen=True)

    isin: str
    name: str | None = None
    index: FloatingRateIndex
    base_index: FloatingRateIndex | None = None
    spread_bps: int | None = None
    day_count: str | None = None
    floor_rate_bps: int | None = None
    cap_rate_bps: int | None = None
    lag_days: int | None = None
    coupon_period_days: int | None = None
    source: str | DataSource = "manual"
    verified_at: date | None = None
    comment: str | None = None
    status: VersionedStatus = VersionedStatus.ACTIVE
    data_quality_status: FormulaDataQuality = FormulaDataQuality.MANUAL
    confidence: Literal["high", "medium", "low"] = "medium"


class RateScenario(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str | None = None
    name: str
    description: str | None = None
    status: VersionedStatus = VersionedStatus.ACTIVE
    created_at: date | None = None
    updated_at: date | None = None
    author: str | None = None
    source: DataSource | None = None
    currency: str | None = None
    market: str | None = None
    time_range: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    index: FloatingRateIndex
    monthly_rates: dict[str, Decimal]


class FloatingCouponForecastEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_uid: str
    figi: str | None = None
    isin: str
    name: str

    coupon_date: date
    source: CouponForecastSource

    index: FloatingRateIndex
    index_rate_percent: Decimal | None = None
    spread_bps: int | None = None
    annual_coupon_rate_percent: Decimal | None = None

    nominal: Decimal
    quantity: Decimal
    coupon_period_days: int | None = None

    coupon_per_bond: Decimal | None = None
    total_coupon: Decimal | None = None

    currency: str = "RUB"


class MonthlyFloatingCouponForecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    month: str
    actual_coupons: Decimal = Decimal("0")
    forecast_coupons: Decimal = Decimal("0")
    unknown_count: int = 0
    total_known_and_forecast: Decimal = Decimal("0")
    currency: str = "RUB"
