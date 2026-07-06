from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.bond_offers import offer_summary_counts
from app.domain.bond_offer import BondOfferEvent, OfferStatus
from app.reporting.cashflow import SCHEMA_VERSION


class OffersAccountReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_label: str
    account_id: str | None = None
    offers: list[BondOfferEvent] = Field(default_factory=list)


class OffersReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = SCHEMA_VERSION
    report_type: str = "offers"
    generated_at: datetime
    as_of: date
    days: int
    warning_days: int
    accounts: list[OffersAccountReport]
    summary: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    data_quality: dict[str, Any] = Field(default_factory=dict)


def build_offers_report(
    *,
    as_of: date,
    days: int,
    warning_days: int,
    account_results: list[OffersAccountReport],
    generated_at: datetime | None = None,
) -> OffersReport:
    offers = [offer for account in account_results for offer in account.offers]
    counts = offer_summary_counts(offers)
    warnings = [
        f"{offer.name}: {offer.event_type.value} in {offer.days_until_offer} days"
        for offer in offers
        if offer.status == OfferStatus.WARNING
    ]
    return OffersReport(
        generated_at=generated_at or datetime.now(timezone.utc),
        as_of=as_of,
        days=days,
        warning_days=warning_days,
        accounts=account_results,
        summary={
            "total_offers": len(offers),
            "within_30_days": counts[30],
            "within_45_days": counts[45],
            "within_90_days": counts[90],
            "warnings_count": len(warnings),
        },
        warnings=warnings,
        data_quality={
            "account_count": len(account_results),
            "event_count": len(offers),
        },
    )
