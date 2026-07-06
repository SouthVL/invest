from datetime import date
from decimal import Decimal

from app.analytics.floating_scenarios import (
    aggregate_monthly_scenarios,
    build_floating_scenario_forecast,
    build_rate_scenarios,
    calculate_coupon_payment,
    estimate_annual_coupon_rate,
    find_last_known_coupon,
)
from app.domain.bond_position import BondCouponScheduleItem
from app.domain.floating_scenarios import (
    CouponSource,
    FloatingScenarioBondPosition,
    ScenarioType,
)


def coupon(day: date, amount: Decimal | None, period: int | None = 91) -> BondCouponScheduleItem:
    return BondCouponScheduleItem(
        coupon_date=day,
        coupon_period_days=period,
        coupon_amount=amount,
        currency="RUB",
    )


def position(coupons: list[BondCouponScheduleItem]) -> FloatingScenarioBondPosition:
    return FloatingScenarioBondPosition(
        instrument_uid="uid1",
        figi="figi1",
        isin="RU000A",
        name="Bond A",
        quantity=Decimal("10"),
        nominal=Decimal("1000"),
        coupons=coupons,
    )


def test_find_last_known_coupon_selects_latest_past_coupon_with_amount() -> None:
    selected = find_last_known_coupon(
        [
            coupon(date(2026, 1, 15), Decimal("40")),
            coupon(date(2026, 3, 15), Decimal("42.50")),
            coupon(date(2026, 6, 15), Decimal("45")),
        ],
        today=date(2026, 5, 1),
    )

    assert selected is not None
    assert selected.coupon_date == date(2026, 3, 15)
    assert selected.coupon_amount == Decimal("42.50")


def test_find_last_known_coupon_uses_latest_known_future_coupon_when_no_past_exists() -> None:
    selected = find_last_known_coupon(
        [
            coupon(date(2026, 6, 15), Decimal("40")),
            coupon(date(2026, 8, 15), Decimal("42.50")),
        ],
        today=date(2026, 5, 1),
    )

    assert selected is not None
    assert selected.coupon_date == date(2026, 8, 15)


def test_find_last_known_coupon_ignores_none_amount() -> None:
    selected = find_last_known_coupon(
        [coupon(date(2026, 3, 15), None), coupon(date(2026, 2, 15), Decimal("41"))],
        today=date(2026, 5, 1),
    )

    assert selected is not None
    assert selected.coupon_amount == Decimal("41")


def test_find_last_known_coupon_ignores_zero_amount() -> None:
    selected = find_last_known_coupon(
        [coupon(date(2026, 3, 15), Decimal("0")), coupon(date(2026, 2, 15), Decimal("41"))],
        today=date(2026, 5, 1),
    )

    assert selected is not None
    assert selected.coupon_amount == Decimal("41")


def test_annualized_rate_is_calculated_from_last_known_coupon() -> None:
    rate = estimate_annual_coupon_rate(
        coupon_amount_per_bond=Decimal("42.50"),
        nominal=Decimal("1000"),
        coupon_period_days=91,
    )

    assert rate.quantize(Decimal("0.01")) == Decimal("17.05")


def test_current_coupon_scenario_reproduces_last_known_coupon_for_same_period_length() -> None:
    rate = estimate_annual_coupon_rate(Decimal("42.50"), Decimal("1000"), 91)
    current_coupon = calculate_coupon_payment(
        nominal=Decimal("1000"),
        annual_coupon_rate_percent=rate,
        coupon_period_days=91,
    )

    assert current_coupon.quantize(Decimal("0.01")) == Decimal("42.50")


def test_coupon_minus_1_percent_lowers_future_coupon() -> None:
    events = build_floating_scenario_forecast(
        positions=[
            position(
                [
                    coupon(date(2026, 3, 15), Decimal("42.50")),
                    coupon(date(2026, 6, 15), None),
                ]
            )
        ],
        months=12,
        delta_percent=Decimal("1.0"),
        start_date=date(2026, 5, 1),
    )

    current = next(event for event in events if event.scenario == ScenarioType.CURRENT_COUPON)
    minus = next(event for event in events if event.scenario == ScenarioType.COUPON_MINUS_1_PERCENT)
    assert minus.coupon_per_bond < current.coupon_per_bond


def test_coupon_plus_1_percent_raises_future_coupon() -> None:
    events = build_floating_scenario_forecast(
        positions=[
            position(
                [
                    coupon(date(2026, 3, 15), Decimal("42.50")),
                    coupon(date(2026, 6, 15), None),
                ]
            )
        ],
        months=12,
        delta_percent=Decimal("1.0"),
        start_date=date(2026, 5, 1),
    )

    current = next(event for event in events if event.scenario == ScenarioType.CURRENT_COUPON)
    plus = next(event for event in events if event.scenario == ScenarioType.COUPON_PLUS_1_PERCENT)
    assert plus.coupon_per_bond > current.coupon_per_bond


def test_actual_future_coupon_overrides_forecast_for_all_scenarios() -> None:
    events = build_floating_scenario_forecast(
        positions=[
            position(
                [
                    coupon(date(2026, 3, 15), Decimal("42.50")),
                    coupon(date(2026, 6, 15), Decimal("43.00")),
                ]
            )
        ],
        months=12,
        delta_percent=Decimal("1.0"),
        start_date=date(2026, 5, 1),
    )

    assert len(events) == 3
    assert all(event.source == CouponSource.ACTUAL for event in events)
    assert all(event.coupon_per_bond == Decimal("43.00") for event in events)
    assert all(event.total_coupon == Decimal("430.00") for event in events)


def test_bond_is_skipped_when_no_known_coupon_exists() -> None:
    events = build_floating_scenario_forecast(
        positions=[position([coupon(date(2026, 6, 15), None)])],
        months=12,
        delta_percent=Decimal("1.0"),
        start_date=date(2026, 5, 1),
    )

    assert events == []


def test_decimal_is_used_everywhere() -> None:
    coupon_value = calculate_coupon_payment(
        nominal=Decimal("1000"),
        annual_coupon_rate_percent=Decimal("0.30"),
        coupon_period_days=1,
    )
    scenarios = build_rate_scenarios(Decimal("0.50"), Decimal("1.0"))

    assert isinstance(coupon_value, Decimal)
    assert all(isinstance(value, Decimal) for value in scenarios.values())


def test_monthly_aggregation_groups_by_month_and_scenario() -> None:
    events = build_floating_scenario_forecast(
        positions=[
            position(
                [
                    coupon(date(2026, 3, 15), Decimal("42.50")),
                    coupon(date(2026, 6, 15), None),
                ]
            )
        ],
        months=12,
        delta_percent=Decimal("1.0"),
        start_date=date(2026, 5, 1),
    )
    rows = aggregate_monthly_scenarios(events)

    assert len(rows) == 3
    assert {row.scenario for row in rows} == set(ScenarioType)
    assert all(row.month == "2026-06" for row in rows)
