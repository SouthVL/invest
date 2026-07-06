from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.domain.bond_offer import BondOfferEvent
from app.reporting.offers import OffersReport


def offers_report_to_dict(report: OffersReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "report_type": report.report_type,
        "generated_at": iso_datetime(report.generated_at),
        "as_of": report.as_of.isoformat(),
        "days": report.days,
        "warning_days": report.warning_days,
        "accounts": [
            {
                "account_label": account.account_label,
                **({"account_id": account.account_id} if account.account_id else {}),
                "offers": [offer_to_dict(offer) for offer in account.offers],
            }
            for account in report.accounts
        ],
        "summary": report.summary,
        "warnings": report.warnings,
        "data_quality": report.data_quality,
    }


def offers_report_to_json(report: OffersReport) -> str:
    return json.dumps(offers_report_to_dict(report), ensure_ascii=False, indent=2) + "\n"


def offer_to_dict(offer: BondOfferEvent) -> dict[str, Any]:
    return {
        "instrument_name": offer.name,
        "figi": offer.figi,
        "isin": offer.isin,
        "offer_date": offer.offer_date.isoformat(),
        "event_type": offer.event_type.value,
        "quantity": decimal_text(offer.quantity),
        "days_until_offer": offer.days_until_offer,
        "status": offer.status.value,
        "source_status": "actual",
    }


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def iso_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
