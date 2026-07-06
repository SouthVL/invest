from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.analytics.cashflow_forecast import _add_months
from app.domain.bond_position import BondCouponScheduleItem
from app.domain.floating_scenarios import (
    CouponSource,
    FloatingScenarioBondPosition,
    FloatingScenarioCouponEvent,
    MonthlyScenarioForecast,
    ScenarioType,
)

DEFAULT_COUPON_PERIOD_DAYS = 91


def estimate_annual_coupon_rate(
    coupon_amount_per_bond: Decimal,
    nominal: Decimal,
    coupon_period_days: int,
) -> Decimal:
    return coupon_amount_per_bond * Decimal("365") / Decimal(coupon_period_days) / nominal * Decimal("100")


def build_rate_scenarios(
    base_rate_percent: Decimal,
    delta_percent: Decimal,
) -> dict[ScenarioType, Decimal]:
    return {
        ScenarioType.CURRENT_COUPON: base_rate_percent,
        ScenarioType.COUPON_MINUS_1_PERCENT: max(base_rate_percent - delta_percent, Decimal("0")),
        ScenarioType.COUPON_PLUS_1_PERCENT: base_rate_percent + delta_percent,
    }


def calculate_coupon_payment(
    nominal: Decimal,
    annual_coupon_rate_percent: Decimal,
    coupon_period_days: int,
) -> Decimal:
    return nominal * annual_coupon_rate_percent / Decimal("100") * Decimal(coupon_period_days) / Decimal("365")


def build_floating_scenario_forecast(
    positions: list[FloatingScenarioBondPosition],
    months: int,
    delta_percent: Decimal,
    start_date: date | None = None,
) -> list[FloatingScenarioCouponEvent]:
    if months < 1:
        raise ValueError("months must be at least 1")
    start = start_date or date.today()
    window_end = _add_months(date(start.year, start.month, 1), months)
    events: list[FloatingScenarioCouponEvent] = []

    for position in positions:
        sorted_coupons = sorted(position.coupons, key=lambda item: item.coupon_date)
        last_known_coupon = find_last_known_coupon(sorted_coupons, start)
        if last_known_coupon is None or position.nominal == Decimal("0"):
            continue
        last_known_period_days = (
            last_known_coupon.coupon_period_days
            or _estimate_coupon_period_days(sorted_coupons, sorted_coupons.index(last_known_coupon))
            or DEFAULT_COUPON_PERIOD_DAYS
        )
        base_coupon = last_known_coupon.coupon_amount or Decimal("0")
        base_rate = estimate_annual_coupon_rate(base_coupon, position.nominal, last_known_period_days)
        scenarios = build_rate_scenarios(base_rate, delta_percent)
        for index, coupon in enumerate(sorted_coupons):
            if coupon.coupon_date < start or coupon.coupon_date >= window_end:
                continue
            period_days = coupon.coupon_period_days or _estimate_coupon_period_days(sorted_coupons, index) or DEFAULT_COUPON_PERIOD_DAYS
            for scenario, rate in scenarios.items():
                coupon_per_bond = coupon.coupon_amount
                source = CouponSource.ACTUAL
                if coupon_per_bond is None:
                    source = CouponSource.FORECAST
                    coupon_per_bond = calculate_coupon_payment(position.nominal, rate, period_days)
                events.append(
                    FloatingScenarioCouponEvent(
                        instrument_uid=position.instrument_uid,
                        isin=position.isin,
                        name=position.name,
                        coupon_date=coupon.coupon_date,
                        scenario=scenario,
                        source=source,
                        base_coupon_per_bond=base_coupon,
                        annual_coupon_rate_percent=rate,
                        nominal=position.nominal,
                        quantity=position.quantity,
                        coupon_period_days=period_days,
                        coupon_per_bond=coupon_per_bond,
                        total_coupon=coupon_per_bond * position.quantity,
                        currency=coupon.currency or position.currency,
                    )
                )
    return sorted(events, key=lambda event: (event.coupon_date, event.name, event.scenario.value))


def find_last_known_coupon(coupons: list[BondCouponScheduleItem], today: date) -> BondCouponScheduleItem | None:
    known = [
        coupon
        for coupon in coupons
        if coupon.coupon_amount is not None and coupon.coupon_amount > Decimal("0")
    ]
    past = sorted((coupon for coupon in known if coupon.coupon_date <= today), key=lambda item: item.coupon_date, reverse=True)
    if past:
        return past[0]
    future = sorted(known, key=lambda item: item.coupon_date, reverse=True)
    return future[0] if future else None


def aggregate_monthly_scenarios(
    events: list[FloatingScenarioCouponEvent],
) -> list[MonthlyScenarioForecast]:
    totals: dict[tuple[str, ScenarioType], Decimal] = {}
    currencies: dict[tuple[str, ScenarioType], str] = {}
    for event in events:
        key = (_month_key(event.coupon_date), event.scenario)
        totals[key] = totals.get(key, Decimal("0")) + event.total_coupon
        currencies[key] = event.currency
    return [
        MonthlyScenarioForecast(
            month=month,
            scenario=scenario,
            total_coupons=totals[(month, scenario)],
            currency=currencies[(month, scenario)],
        )
        for month, scenario in sorted(totals, key=lambda item: (item[0], item[1].value))
    ]


def _estimate_coupon_period_days(coupons: list[BondCouponScheduleItem], index: int) -> int | None:
    current = coupons[index].coupon_date
    if index > 0:
        return (current - coupons[index - 1].coupon_date).days
    if index + 1 < len(coupons):
        return (coupons[index + 1].coupon_date - current).days
    return None


def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"
