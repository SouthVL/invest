from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from app.analytics.bond_offers import filter_and_sort_offers, offer_status
from app.domain.bond_offer import BondOfferEvent, OfferEventType
from invest_bonds.adapter import _enum_name
from invest_bonds.money import quotation_to_decimal
from invest_bonds.sdk_compat import configure_t_invest_sdk

logger = logging.getLogger(__name__)


class TInvestBondOfferService:
    def __init__(self, client):
        self.client = client

    def get_upcoming_offers(
        self,
        account_id: str,
        from_date: date,
        to_date: date,
        *,
        warning_days: int = 45,
    ) -> list[BondOfferEvent]:
        configure_t_invest_sdk()
        portfolio = self.client.operations.get_portfolio(account_id=account_id)
        offers: list[BondOfferEvent] = []

        for position in portfolio.positions:
            if (getattr(position, "instrument_type", "") or "").lower() != "bond":
                continue
            quantity = quotation_to_decimal(getattr(position, "quantity", None)) or Decimal("0")
            if quantity <= Decimal("0"):
                continue
            try:
                offers.extend(self._position_offers(position, quantity, from_date, to_date, warning_days))
            except Exception as exc:  # pragma: no cover - exercised with fake client tests
                logger.warning("Could not fetch bond events for %s: %s", getattr(position, "figi", ""), exc)

        return filter_and_sort_offers(offers, as_of=from_date, days=(to_date - from_date).days)

    def _position_offers(
        self,
        position: Any,
        quantity: Decimal,
        from_date: date,
        to_date: date,
        warning_days: int,
    ) -> list[BondOfferEvent]:
        from t_tech.invest.schemas import EventType, GetBondEventsRequest, InstrumentIdType

        figi = getattr(position, "figi", "") or None
        position_uid = getattr(position, "instrument_uid", "") or ""
        instrument_id = position_uid or figi or ""
        id_type = InstrumentIdType.INSTRUMENT_ID_TYPE_UID if position_uid else InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI
        bond = self.client.instruments.bond_by(id_type=id_type, id=instrument_id).instrument
        uid = getattr(bond, "uid", "") or position_uid or figi or ""
        response = self.client.instruments.get_bond_events(
            GetBondEventsRequest(
                from_=_day_start(from_date),
                to=_day_end(to_date),
                instrument_id=uid,
                type=EventType.EVENT_TYPE_UNSPECIFIED,
            )
        )

        offers: list[BondOfferEvent] = []
        for event in response.events:
            event_type = classify_offer_event(event, EventType)
            if event_type is None:
                continue
            offer_date = _event_date(event)
            if offer_date is None:
                continue
            days_until = (offer_date - from_date).days
            offers.append(
                BondOfferEvent(
                    instrument_uid=uid,
                    figi=getattr(bond, "figi", None) or figi,
                    isin=getattr(bond, "isin", ""),
                    name=getattr(bond, "name", ""),
                    offer_date=offer_date,
                    event_type=event_type,
                    quantity=quantity,
                    days_until_offer=days_until,
                    status=offer_status(offer_date, from_date, warning_days),
                )
            )
        return offers


def classify_offer_event(event: Any, sdk_event_type: Any) -> OfferEventType | None:
    if getattr(event, "event_type", None) == sdk_event_type.EVENT_TYPE_CALL:
        return OfferEventType.CALL

    text = " ".join(
        [
            _enum_name(getattr(event, "event_type", "")),
            getattr(event, "operation_type", ""),
            getattr(event, "execution", ""),
            getattr(event, "note", ""),
        ]
    ).lower()
    if not text.strip():
        return None
    if "buyback" in text or "buy back" in text or "выкуп" in text:
        return OfferEventType.BUYBACK
    if "put" in text or "оферта put" in text:
        return OfferEventType.PUT
    if "call" in text or "early redemption" in text or "досроч" in text:
        return OfferEventType.CALL
    if "offer" in text or "оферт" in text:
        return OfferEventType.OFFER
    return None


def _event_date(event: Any) -> date | None:
    return _to_date(getattr(event, "pay_date", None)) or _to_date(getattr(event, "event_date", None))


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _day_end(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.year <= 1970:
            return None
        return value.date()
    if isinstance(value, date):
        if value.year <= 1970:
            return None
        return value
    return None
