from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.domain.bond_position import BondCouponScheduleItem


class ScenarioType(StrEnum):
    CURRENT_COUPON = "current_coupon"
    COUPON_MINUS_1_PERCENT = "coupon_minus_1_percent"
    COUPON_PLUS_1_PERCENT = "coupon_plus_1_percent"


class CouponSource(StrEnum):
    ACTUAL = "actual"
    FORECAST = "forecast"
    SKIPPED = "skipped"


class FloatingScenarioBondPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_uid: str
    figi: str | None = None
    isin: str
    name: str
    quantity: Decimal
    nominal: Decimal
    currency: str = "RUB"
    coupons: list[BondCouponScheduleItem]


class FloatingScenarioCouponEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_uid: str
    isin: str
    name: str

    coupon_date: date

    scenario: ScenarioType
    source: CouponSource

    base_coupon_per_bond: Decimal
    annual_coupon_rate_percent: Decimal

    nominal: Decimal
    quantity: Decimal
    coupon_period_days: int

    coupon_per_bond: Decimal
    total_coupon: Decimal

    currency: str = "RUB"


class MonthlyScenarioForecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    month: str

    scenario: ScenarioType

    total_coupons: Decimal

    currency: str = "RUB"
