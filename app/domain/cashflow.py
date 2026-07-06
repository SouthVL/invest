from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CashflowType(StrEnum):
    COUPON = "coupon"
    DIVIDEND = "dividend"
    AMORTIZATION = "amortization"
    MATURITY = "maturity"


class CashflowSource(StrEnum):
    ACTUAL = "actual"
    FLOATING_COUPON = "floating_coupon"
    REPEATED_FLOATING_COUPON = "repeated_floating_coupon"


class CashflowEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_uid: str
    figi: str | None = None
    isin: str | None = None
    name: str

    event_date: date
    event_type: CashflowType

    amount_per_bond: Decimal
    quantity: Decimal
    total_amount: Decimal

    currency: str = "RUB"
    payment_amount_per_unit: Decimal | None = None
    payment_total_amount: Decimal | None = None
    payment_currency: str | None = None
    source: CashflowSource = CashflowSource.ACTUAL


class MonthlyCashflow(BaseModel):
    model_config = ConfigDict(frozen=True)

    month: str
    coupons: Decimal = Decimal("0")
    fixed_coupons: Decimal = Decimal("0")
    floating_coupons: Decimal = Decimal("0")
    dividends: Decimal = Decimal("0")
    amortizations: Decimal = Decimal("0")
    maturities: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    currency: str = "RUB"
