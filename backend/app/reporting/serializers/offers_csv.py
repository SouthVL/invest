from __future__ import annotations

import csv
from io import StringIO

from app.domain.bond_offer import BondOfferEvent
from app.reporting.offers import OffersReport
from app.reporting.serializers.offers_json import decimal_text

OFFERS_HEADER = [
    "account_label",
    "offer_date",
    "event_type",
    "instrument_name",
    "isin",
    "figi",
    "quantity",
    "days_until_offer",
    "status",
    "source_status",
]


def offers_to_csv(report: OffersReport) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(OFFERS_HEADER)
    for account in report.accounts:
        for offer in account.offers:
            writer.writerow(offer_row(account.account_label, offer))
    return output.getvalue()


def offer_row(account_label: str, offer: BondOfferEvent) -> list[str]:
    return [
        account_label,
        offer.offer_date.isoformat(),
        offer.event_type.value,
        offer.name,
        offer.isin,
        offer.figi or "",
        decimal_text(offer.quantity),
        str(offer.days_until_offer),
        offer.status.value,
        "actual",
    ]
