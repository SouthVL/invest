from datetime import date, timedelta
from decimal import Decimal

from invest_bonds.models import BondCoupon, BondEvent, BondEventType, BondInstrument, Signal
from invest_bonds.rules import analyze_bond


def instrument(maturity_date: date | None = None) -> BondInstrument:
    return BondInstrument(uid="uid-1", name="Bond", maturity_date=maturity_date, nominal=Decimal("1000"))


def coupon(day: date) -> BondCoupon:
    return BondCoupon(instrument_uid="uid-1", coupon_date=day)


def event(event_type: BondEventType, day: date) -> BondEvent:
    return BondEvent(instrument_uid="uid-1", event_type=event_type, event_date=day)


def test_offer_within_45_days_checks_rebalance() -> None:
    as_of = date(2026, 4, 27)
    analysis = analyze_bond(
        instrument=instrument(),
        coupons=[coupon(as_of + timedelta(days=90))],
        events=[event(BondEventType.CALL, as_of + timedelta(days=45))],
        as_of=as_of,
    )
    assert analysis.signal == Signal.CHECK_REBALANCE


def test_maturity_within_60_days_finds_replacement() -> None:
    as_of = date(2026, 4, 27)
    analysis = analyze_bond(
        instrument=instrument(maturity_date=as_of + timedelta(days=60)),
        coupons=[coupon(as_of + timedelta(days=20))],
        events=[],
        as_of=as_of,
    )
    assert analysis.signal == Signal.FIND_REPLACEMENT


def test_no_future_coupon_checks_data() -> None:
    as_of = date(2026, 4, 27)
    analysis = analyze_bond(instrument=instrument(), coupons=[], events=[], as_of=as_of)
    assert analysis.signal == Signal.CHECK_DATA


def test_normal_future_coupon_holds() -> None:
    as_of = date(2026, 4, 27)
    analysis = analyze_bond(
        instrument=instrument(maturity_date=as_of + timedelta(days=400)),
        coupons=[coupon(as_of + timedelta(days=30))],
        events=[],
        as_of=as_of,
    )
    assert analysis.signal == Signal.HOLD


def test_offer_wins_over_maturity() -> None:
    as_of = date(2026, 4, 27)
    analysis = analyze_bond(
        instrument=instrument(maturity_date=as_of + timedelta(days=10)),
        coupons=[coupon(as_of + timedelta(days=90))],
        events=[event(BondEventType.CALL, as_of + timedelta(days=5))],
        as_of=as_of,
    )
    assert analysis.signal == Signal.CHECK_REBALANCE
