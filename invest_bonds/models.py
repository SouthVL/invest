from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Signal(StrEnum):
    CHECK_REBALANCE = "CHECK_REBALANCE"
    FIND_REPLACEMENT = "FIND_REPLACEMENT"
    CHECK_DATA = "CHECK_DATA"
    HOLD = "HOLD"


class BondEventType(StrEnum):
    COUPON = "COUPON"
    CALL = "CALL"
    MATURITY = "MATURITY"
    OTHER = "OTHER"


class AccountSummary(BaseModel):
    id: str
    name: str = ""
    type: str = ""
    status: str = ""
    access_level: str = ""


class BondInstrument(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    uid: str
    position_uid: str = ""
    figi: str = ""
    isin: str = ""
    name: str = ""
    nominal: Decimal | None = None
    nominal_currency: str | None = None
    maturity_date: date | None = None
    coupon_quantity_per_year: int | None = None
    floating_coupon_flag: bool = False
    perpetual_flag: bool = False
    amortization_flag: bool = False


class BondPosition(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    figi: str = ""
    ticker: str = ""
    instrument_uid: str
    position_uid: str = ""
    quantity: Decimal = Decimal("0")
    quantity_lots: Decimal = Decimal("0")
    average_position_price: Decimal | None = None
    current_price: Decimal | None = None
    price_currency: str | None = None
    expected_yield: Decimal | None = None


class BondCoupon(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    instrument_uid: str
    figi: str = ""
    coupon_date: date
    pay_one_bond: Decimal | None = None
    currency: str | None = None
    coupon_type: str = ""
    coupon_period: int | None = None


class BondEvent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    instrument_uid: str
    event_type: BondEventType
    event_date: date | None = None
    pay_date: date | None = None
    amount: Decimal | None = None
    currency: str | None = None
    value: Decimal | None = None
    note: str = ""

    @property
    def important_date(self) -> date | None:
        return self.event_date or self.pay_date


class BondAnalysis(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    signal: Signal
    nearest_event_date: date | None = None
    nearest_event_type: str = ""
    next_coupon_date: date | None = None
    next_offer_date: date | None = None


class BondHolding(BaseModel):
    instrument: BondInstrument
    position: BondPosition
    coupons: list[BondCoupon] = Field(default_factory=list)
    events: list[BondEvent] = Field(default_factory=list)
    analysis: BondAnalysis


class BondSnapshot(BaseModel):
    account_id: str
    fetched_at: datetime
    as_of: date
    holdings: list[BondHolding] = Field(default_factory=list)
