from __future__ import annotations

from decimal import Decimal
from typing import Any

NANO = Decimal("1000000000")


def units_nano_to_decimal(units: int | None, nano: int | None) -> Decimal:
    return Decimal(units or 0) + (Decimal(nano or 0) / NANO)


def money_to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return units_nano_to_decimal(getattr(value, "units", 0), getattr(value, "nano", 0))


def quotation_to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return units_nano_to_decimal(getattr(value, "units", 0), getattr(value, "nano", 0))


def money_currency(value: Any) -> str | None:
    if value is None:
        return None
    currency = getattr(value, "currency", None)
    return currency or None
