from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PortfolioAsset(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_id: str
    instrument_uid: str
    position_uid: str = ""
    figi: str = ""
    ticker: str = ""
    instrument_type: str = ""
    name: str = ""
    isin: str = ""
    quantity: Decimal
    average_position_price: Decimal | None = None
    current_price: Decimal | None = None
    price_currency: str | None = None


class PortfolioSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_id: str
    fetched_at: datetime
    as_of: date
    assets: list[PortfolioAsset] = Field(default_factory=list)
    total_value: Decimal | None = None
    total_value_currency: str | None = None
