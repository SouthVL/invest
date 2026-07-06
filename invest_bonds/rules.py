from __future__ import annotations

from datetime import date

from invest_bonds.models import BondAnalysis, BondCoupon, BondEvent, BondEventType, BondInstrument, Signal

OFFER_WINDOW_DAYS = 45
MATURITY_WINDOW_DAYS = 60


def future_coupons(coupons: list[BondCoupon], as_of: date) -> list[BondCoupon]:
    return sorted((coupon for coupon in coupons if coupon.coupon_date >= as_of), key=lambda item: item.coupon_date)


def future_events(events: list[BondEvent], as_of: date, event_type: BondEventType) -> list[BondEvent]:
    return sorted(
        (
            event
            for event in events
            if event.event_type == event_type and event.important_date is not None and event.important_date >= as_of
        ),
        key=lambda item: item.important_date or date.max,
    )


def days_until(value: date | None, as_of: date) -> int | None:
    if value is None:
        return None
    return (value - as_of).days


def analyze_bond(
    *,
    instrument: BondInstrument,
    coupons: list[BondCoupon],
    events: list[BondEvent],
    as_of: date,
) -> BondAnalysis:
    next_coupons = future_coupons(coupons, as_of)
    next_coupon_date = next_coupons[0].coupon_date if next_coupons else None

    next_calls = future_events(events, as_of, BondEventType.CALL)
    next_offer_date = next_calls[0].important_date if next_calls else None

    maturity_date = instrument.maturity_date
    event_maturities = future_events(events, as_of, BondEventType.MATURITY)
    if event_maturities:
        maturity_date = event_maturities[0].important_date

    signal = Signal.HOLD
    offer_days = days_until(next_offer_date, as_of)
    maturity_days = days_until(maturity_date, as_of)
    if offer_days is not None and 0 <= offer_days <= OFFER_WINDOW_DAYS:
        signal = Signal.CHECK_REBALANCE
    elif maturity_days is not None and 0 <= maturity_days <= MATURITY_WINDOW_DAYS:
        signal = Signal.FIND_REPLACEMENT
    elif next_coupon_date is None:
        signal = Signal.CHECK_DATA

    nearest_date, nearest_type = nearest_event(
        next_offer_date=next_offer_date,
        maturity_date=maturity_date,
        next_coupon_date=next_coupon_date,
    )
    return BondAnalysis(
        signal=signal,
        nearest_event_date=nearest_date,
        nearest_event_type=nearest_type,
        next_coupon_date=next_coupon_date,
        next_offer_date=next_offer_date,
    )


def nearest_event(
    *,
    next_offer_date: date | None,
    maturity_date: date | None,
    next_coupon_date: date | None,
) -> tuple[date | None, str]:
    candidates = [
        (next_offer_date, "CALL", 0),
        (maturity_date, "MATURITY", 1),
        (next_coupon_date, "COUPON", 2),
    ]
    dated = [candidate for candidate in candidates if candidate[0] is not None]
    if not dated:
        return None, ""
    event_date, event_type, _ = min(dated, key=lambda item: (item[0] or date.max, item[2]))
    return event_date, event_type
