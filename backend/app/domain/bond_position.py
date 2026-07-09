from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BondCouponScheduleItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    coupon_date: date
    coupon_period_days: int | None = None
    coupon_amount: Decimal | None = None
    coupon_type: str = ""
    currency: str = "RUB"


class BondPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_uid: str
    figi: str | None = None
    isin: str
    name: str
    quantity: Decimal
    nominal: Decimal
    currency: str = "RUB"
    coupons: list[BondCouponScheduleItem]
