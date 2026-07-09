from __future__ import annotations

from datetime import date

from app.domain.bond_offer import BondOfferEvent, OfferStatus


def offer_status(offer_date: date, as_of: date, warning_days: int) -> OfferStatus:
    days = (offer_date - as_of).days
    if days < 0:
        return OfferStatus.EXPIRED
    if days <= warning_days:
        return OfferStatus.WARNING
    return OfferStatus.OK


def filter_and_sort_offers(
    offers: list[BondOfferEvent],
    *,
    as_of: date,
    days: int,
) -> list[BondOfferEvent]:
    window_end = as_of.toordinal() + days
    return sorted(
        (offer for offer in offers if offer.days_until_offer >= 0 and offer.offer_date.toordinal() <= window_end),
        key=lambda offer: (offer.offer_date, offer.name),
    )


def offer_summary_counts(offers: list[BondOfferEvent]) -> dict[int, int]:
    return {
        30: sum(1 for offer in offers if offer.days_until_offer <= 30),
        45: sum(1 for offer in offers if offer.days_until_offer <= 45),
        90: sum(1 for offer in offers if offer.days_until_offer <= 90),
    }
