from datetime import date
from decimal import Decimal

from app.analytics.floating_coupon_forecast import (
    aggregate_monthly_floating_forecast,
    build_floating_coupon_forecast,
    calculate_floating_coupon_per_bond,
)
from app.domain.bond_position import BondCouponScheduleItem, BondPosition
from app.domain.floating_coupon import (
    CouponForecastSource,
    FloatingCouponFormula,
    FloatingRateIndex,
    RateScenario,
)


def position(coupon_amount: Decimal | None = None, coupon_date: date = date(2026, 5, 15)) -> BondPosition:
    return BondPosition(
        instrument_uid="uid1",
        figi="figi1",
        isin="RU000A",
        name="Bond A",
        quantity=Decimal("10"),
        nominal=Decimal("1000"),
        coupons=[
            BondCouponScheduleItem(
                coupon_date=coupon_date,
                coupon_period_days=91,
                coupon_amount=coupon_amount,
                currency="RUB",
            )
        ],
    )


def formula(**kwargs) -> FloatingCouponFormula:
    return FloatingCouponFormula(
        isin="RU000A",
        index=FloatingRateIndex.KEY_RATE,
        spread_bps=130,
        coupon_period_days=91,
        **kwargs,
    )


def scenario(rates: dict[str, Decimal] | None = None) -> RateScenario:
    return RateScenario(
        name="base",
        index=FloatingRateIndex.KEY_RATE,
        monthly_rates={"2026-05": Decimal("16.00"), "2026-06": Decimal("15.00")} if rates is None else rates,
    )


def test_calculates_key_rate_plus_spread_coupon_correctly() -> None:
    result = calculate_floating_coupon_per_bond(
        nominal=Decimal("1000"),
        index_rate_percent=Decimal("16.00"),
        spread_bps=130,
        coupon_period_days=91,
    )

    assert result.quantize(Decimal("0.01")) == Decimal("43.13")


def test_applies_floor_rate() -> None:
    result = calculate_floating_coupon_per_bond(
        nominal=Decimal("1000"),
        index_rate_percent=Decimal("10.00"),
        spread_bps=0,
        coupon_period_days=365,
        floor_rate_bps=1200,
    )

    assert result == Decimal("120")


def test_applies_cap_rate() -> None:
    result = calculate_floating_coupon_per_bond(
        nominal=Decimal("1000"),
        index_rate_percent=Decimal("20.00"),
        spread_bps=0,
        coupon_period_days=365,
        cap_rate_bps=1500,
    )

    assert result == Decimal("150")


def test_uses_actual_coupon_over_forecast() -> None:
    events = build_floating_coupon_forecast(
        bond_positions=[position(coupon_amount=Decimal("35.25"))],
        formulas_by_isin={"RU000A": formula()},
        scenario=scenario(),
        start_date=date(2026, 5, 1),
        months=1,
    )

    assert events[0].source == CouponForecastSource.ACTUAL
    assert events[0].coupon_per_bond == Decimal("35.25")
    assert events[0].total_coupon == Decimal("352.50")


def test_produces_unknown_when_formula_is_missing() -> None:
    events = build_floating_coupon_forecast(
        bond_positions=[position()],
        formulas_by_isin={},
        scenario=scenario(),
        start_date=date(2026, 5, 1),
        months=1,
    )

    assert events[0].source == CouponForecastSource.UNKNOWN
    assert events[0].total_coupon is None


def test_produces_unknown_when_scenario_rate_is_missing() -> None:
    events = build_floating_coupon_forecast(
        bond_positions=[position()],
        formulas_by_isin={"RU000A": formula()},
        scenario=scenario(rates={}),
        start_date=date(2026, 5, 1),
        months=1,
    )

    assert events[0].source == CouponForecastSource.UNKNOWN
    assert events[0].index == FloatingRateIndex.KEY_RATE


def test_aggregates_actual_and_forecast_coupons_separately() -> None:
    actual = build_floating_coupon_forecast(
        bond_positions=[position(coupon_amount=Decimal("35.25"))],
        formulas_by_isin={"RU000A": formula()},
        scenario=scenario(),
        start_date=date(2026, 5, 1),
        months=1,
    )[0]
    forecast = build_floating_coupon_forecast(
        bond_positions=[position(coupon_amount=None)],
        formulas_by_isin={"RU000A": formula()},
        scenario=scenario(),
        start_date=date(2026, 5, 1),
        months=1,
    )[0]

    rows = aggregate_monthly_floating_forecast([actual, forecast], start_date=date(2026, 5, 1), months=1)

    assert rows[0].actual_coupons == Decimal("352.50")
    assert rows[0].forecast_coupons == forecast.total_coupon
    assert rows[0].total_known_and_forecast == Decimal("352.50") + (forecast.total_coupon or Decimal("0"))


def test_includes_empty_months() -> None:
    rows = aggregate_monthly_floating_forecast([], start_date=date(2026, 5, 1), months=2)

    assert [row.month for row in rows] == ["2026-05", "2026-06"]
    assert rows[0].total_known_and_forecast == Decimal("0")
    assert rows[1].unknown_count == 0


def test_ignores_events_outside_forecast_window() -> None:
    events = build_floating_coupon_forecast(
        bond_positions=[position(coupon_date=date(2026, 7, 1))],
        formulas_by_isin={"RU000A": formula()},
        scenario=scenario(),
        start_date=date(2026, 5, 1),
        months=2,
    )

    rows = aggregate_monthly_floating_forecast(events, start_date=date(2026, 5, 1), months=2)

    assert events == []
    assert [row.total_known_and_forecast for row in rows] == [Decimal("0"), Decimal("0")]


def test_never_uses_float_for_money_calculations() -> None:
    result = calculate_floating_coupon_per_bond(
        nominal=Decimal("1000"),
        index_rate_percent=Decimal("0.10"),
        spread_bps=20,
        coupon_period_days=1,
    )

    assert isinstance(result, Decimal)
    assert result == Decimal("1000") * Decimal("0.30") / Decimal("100") * Decimal("1") / Decimal("365")
