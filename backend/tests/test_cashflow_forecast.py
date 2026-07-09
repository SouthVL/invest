from datetime import date
from decimal import Decimal

from app.analytics.cashflow_forecast import build_monthly_cashflow
from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType


def event(
    event_date: date,
    event_type: CashflowType,
    total: str,
    source: CashflowSource = CashflowSource.ACTUAL,
) -> CashflowEvent:
    return CashflowEvent(
        instrument_uid="uid1",
        figi="figi1",
        isin="RU000A",
        name="Bond A",
        event_date=event_date,
        event_type=event_type,
        amount_per_bond=Decimal("1"),
        quantity=Decimal("1"),
        total_amount=Decimal(total),
        currency="RUB",
        source=source,
    )


def test_groups_coupons_by_month() -> None:
    rows = build_monthly_cashflow(
        [event(date(2026, 5, 15), CashflowType.COUPON, "352.50")],
        start_date=date(2026, 5, 1),
        months=2,
    )

    assert rows[0].month == "2026-05"
    assert rows[0].coupons == Decimal("352.50")
    assert rows[0].fixed_coupons == Decimal("352.50")
    assert rows[0].floating_coupons == Decimal("0")
    assert rows[1].month == "2026-06"
    assert rows[1].coupons == Decimal("0")


def test_separates_coupons_amortizations_and_maturities() -> None:
    rows = build_monthly_cashflow(
        [
            event(date(2026, 5, 15), CashflowType.COUPON, "352.50"),
            event(date(2026, 5, 20), CashflowType.AMORTIZATION, "1000"),
            event(date(2026, 5, 25), CashflowType.MATURITY, "5000"),
        ],
        start_date=date(2026, 5, 1),
        months=1,
    )

    assert rows[0].coupons == Decimal("352.50")
    assert rows[0].amortizations == Decimal("1000")
    assert rows[0].maturities == Decimal("5000")


def test_separates_dividends_from_bond_cashflow() -> None:
    rows = build_monthly_cashflow(
        [
            event(date(2026, 5, 15), CashflowType.COUPON, "352.50"),
            event(date(2026, 5, 20), CashflowType.DIVIDEND, "125.75"),
        ],
        start_date=date(2026, 5, 1),
        months=1,
    )

    assert rows[0].coupons == Decimal("352.50")
    assert rows[0].dividends == Decimal("125.75")
    assert rows[0].total == Decimal("478.25")


def test_separates_floating_coupons_from_fixed_coupons() -> None:
    rows = build_monthly_cashflow(
        [
            event(date(2026, 5, 15), CashflowType.COUPON, "100", source=CashflowSource.ACTUAL),
            event(date(2026, 5, 20), CashflowType.COUPON, "200", source=CashflowSource.FLOATING_COUPON),
            event(date(2026, 5, 25), CashflowType.COUPON, "300", source=CashflowSource.REPEATED_FLOATING_COUPON),
        ],
        start_date=date(2026, 5, 1),
        months=1,
    )

    assert rows[0].fixed_coupons == Decimal("100")
    assert rows[0].floating_coupons == Decimal("500")
    assert rows[0].coupons == Decimal("600")


def test_includes_empty_months() -> None:
    rows = build_monthly_cashflow([], start_date=date(2026, 5, 1), months=3)

    assert [row.month for row in rows] == ["2026-05", "2026-06", "2026-07"]
    assert all(row.total == Decimal("0") for row in rows)


def test_ignores_events_before_start_date() -> None:
    rows = build_monthly_cashflow(
        [event(date(2026, 4, 30), CashflowType.COUPON, "10")],
        start_date=date(2026, 5, 1),
        months=1,
    )

    assert rows[0].total == Decimal("0")


def test_ignores_events_after_forecast_window() -> None:
    rows = build_monthly_cashflow(
        [event(date(2026, 7, 1), CashflowType.COUPON, "10")],
        start_date=date(2026, 5, 1),
        months=2,
    )

    assert [row.total for row in rows] == [Decimal("0"), Decimal("0")]


def test_handles_multiple_events_in_same_month() -> None:
    rows = build_monthly_cashflow(
        [
            event(date(2026, 5, 1), CashflowType.COUPON, "10.10"),
            event(date(2026, 5, 2), CashflowType.COUPON, "20.20"),
        ],
        start_date=date(2026, 5, 1),
        months=1,
    )

    assert rows[0].coupons == Decimal("30.30")


def test_uses_decimal_not_float() -> None:
    rows = build_monthly_cashflow(
        [
            event(date(2026, 5, 1), CashflowType.COUPON, "0.10"),
            event(date(2026, 5, 2), CashflowType.COUPON, "0.20"),
        ],
        start_date=date(2026, 5, 1),
        months=1,
    )

    assert rows[0].coupons == Decimal("0.30")


def test_correctly_calculates_total() -> None:
    rows = build_monthly_cashflow(
        [
            event(date(2026, 5, 15), CashflowType.COUPON, "352.50"),
            event(date(2026, 5, 20), CashflowType.AMORTIZATION, "1000"),
            event(date(2026, 6, 10), CashflowType.MATURITY, "5000"),
        ],
        start_date=date(2026, 5, 1),
        months=2,
    )

    assert rows[0].total == Decimal("1352.50")
    assert rows[1].total == Decimal("5000")
