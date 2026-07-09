from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class OfferStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    EXPIRED = "expired"


class OfferEventType(StrEnum):
    OFFER = "offer"
    PUT = "put"
    CALL = "call"
    BUYBACK = "buyback"
    UNKNOWN = "unknown"


class BondOfferEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_uid: str
    figi: str | None = None
    isin: str
    name: str

    offer_date: date

    event_type: OfferEventType

    quantity: Decimal

    days_until_offer: int

    status: OfferStatus
