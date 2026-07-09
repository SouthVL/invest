from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TypedDict

from app.analytics.cashflow_forecast import _add_months
from app.domain.bond_position import BondPosition
from app.domain.floating_coupon import (
    CouponForecastSource,
    FormulaDataQuality,
    FloatingCouponForecastEvent,
    FloatingCouponFormula,
    FloatingRateIndex,
    MonthlyFloatingCouponForecast,
    RateScenario,
    VersionedStatus,
)


class MonthlyFloatingBucket(TypedDict):
    actual: Decimal
    forecast: Decimal
    unknown: int
    currency: str


def calculate_floating_coupon_per_bond(
    nominal: Decimal,
    index_rate_percent: Decimal,
    spread_bps: int,
    coupon_period_days: int,
    floor_rate_bps: int | None = None,
    cap_rate_bps: int | None = None,
) -> Decimal:
    annual_coupon_rate_percent = index_rate_percent + (Decimal(spread_bps) / Decimal("100"))
    if floor_rate_bps is not None:
        annual_coupon_rate_percent = max(annual_coupon_rate_percent, Decimal(floor_rate_bps) / Decimal("100"))
    if cap_rate_bps is not None:
        annual_coupon_rate_percent = min(annual_coupon_rate_percent, Decimal(cap_rate_bps) / Decimal("100"))
    return nominal * annual_coupon_rate_percent / Decimal("100") * Decimal(coupon_period_days) / Decimal("365")


def build_floating_coupon_forecast(
    bond_positions: list[BondPosition],
    formulas_by_isin: dict[str, FloatingCouponFormula],
    scenario: RateScenario,
    start_date: date,
    months: int,
) -> list[FloatingCouponForecastEvent]:
    if months < 1:
        raise ValueError("months must be at least 1")

    window_end = _add_months(date(start_date.year, start_date.month, 1), months)
    events: list[FloatingCouponForecastEvent] = []
    for position in bond_positions:
        sorted_coupons = sorted(position.coupons, key=lambda item: item.coupon_date)
        for index, coupon in enumerate(sorted_coupons):
            if coupon.coupon_date < start_date or coupon.coupon_date >= window_end:
                continue
            formula = formulas_by_isin.get(position.isin)
            period_days = (
                coupon.coupon_period_days
                or _estimate_coupon_period_days(sorted_coupons, index)
                or (formula.coupon_period_days if formula else None)
                or 91
            )

            if coupon.coupon_amount is not None:
                total = coupon.coupon_amount * position.quantity
                events.append(
                    FloatingCouponForecastEvent(
                        instrument_uid=position.instrument_uid,
                        figi=position.figi,
                        isin=position.isin,
                        name=position.name,
                        coupon_date=coupon.coupon_date,
                        source=CouponForecastSource.ACTUAL,
                        index=formula.index if formula else FloatingRateIndex.UNKNOWN,
                        nominal=position.nominal,
                        quantity=position.quantity,
                        coupon_period_days=period_days,
                        coupon_per_bond=coupon.coupon_amount,
                        total_coupon=total,
                        currency=coupon.currency or position.currency,
                    )
                )
                continue

            if formula is None or not formula_is_usable(formula):
                events.append(_unknown_event(position, coupon.coupon_date, period_days))
                continue

            month = _month_key(coupon.coupon_date)
            index_rate = scenario.monthly_rates.get(month) if scenario.index == formula.index else None
            if index_rate is None:
                events.append(_unknown_event(position, coupon.coupon_date, period_days, formula=formula))
                continue

            spread = formula.spread_bps or 0
            coupon_per_bond = calculate_floating_coupon_per_bond(
                nominal=position.nominal,
                index_rate_percent=index_rate,
                spread_bps=spread,
                coupon_period_days=period_days,
                floor_rate_bps=formula.floor_rate_bps,
                cap_rate_bps=formula.cap_rate_bps,
            )
            annual_rate = _annual_rate(index_rate, spread, formula.floor_rate_bps, formula.cap_rate_bps)
            events.append(
                FloatingCouponForecastEvent(
                    instrument_uid=position.instrument_uid,
                    figi=position.figi,
                    isin=position.isin,
                    name=position.name,
                    coupon_date=coupon.coupon_date,
                    source=CouponForecastSource.FORECAST,
                    index=formula.index,
                    index_rate_percent=index_rate,
                    spread_bps=spread,
                    annual_coupon_rate_percent=annual_rate,
                    nominal=position.nominal,
                    quantity=position.quantity,
                    coupon_period_days=period_days,
                    coupon_per_bond=coupon_per_bond,
                    total_coupon=coupon_per_bond * position.quantity,
                    currency=position.currency,
                )
            )
    return sorted(events, key=lambda event: (event.coupon_date, event.name, event.isin))


def aggregate_monthly_floating_forecast(
    events: list[FloatingCouponForecastEvent],
    start_date: date,
    months: int,
) -> list[MonthlyFloatingCouponForecast]:
    if months < 1:
        raise ValueError("months must be at least 1")

    start_month = date(start_date.year, start_date.month, 1)
    month_keys = [_month_key(_add_months(start_month, offset)) for offset in range(months)]
    window_end = _add_months(start_month, months)
    buckets: dict[str, MonthlyFloatingBucket] = {
        month: {
            "actual": Decimal("0"),
            "forecast": Decimal("0"),
            "unknown": 0,
            "currency": "RUB",
        }
        for month in month_keys
    }

    for event in events:
        if event.coupon_date < start_date or event.coupon_date >= window_end:
            continue
        month = _month_key(event.coupon_date)
        if month not in buckets:
            continue
        buckets[month]["currency"] = event.currency
        if event.source == CouponForecastSource.ACTUAL:
            buckets[month]["actual"] += event.total_coupon or Decimal("0")
        elif event.source == CouponForecastSource.FORECAST:
            buckets[month]["forecast"] += event.total_coupon or Decimal("0")
        else:
            buckets[month]["unknown"] += 1

    return [
        MonthlyFloatingCouponForecast(
            month=month,
            actual_coupons=buckets[month]["actual"],
            forecast_coupons=buckets[month]["forecast"],
            unknown_count=buckets[month]["unknown"],
            total_known_and_forecast=buckets[month]["actual"] + buckets[month]["forecast"],
            currency=buckets[month]["currency"],
        )
        for month in month_keys
    ]


def _unknown_event(
    position: BondPosition,
    coupon_date: date,
    period_days: int,
    formula: FloatingCouponFormula | None = None,
) -> FloatingCouponForecastEvent:
    return FloatingCouponForecastEvent(
        instrument_uid=position.instrument_uid,
        figi=position.figi,
        isin=position.isin,
        name=position.name,
        coupon_date=coupon_date,
        source=CouponForecastSource.UNKNOWN,
        index=formula.index if formula else FloatingRateIndex.UNKNOWN,
        spread_bps=formula.spread_bps if formula else None,
        nominal=position.nominal,
        quantity=position.quantity,
        coupon_period_days=period_days,
        currency=position.currency,
    )


def formula_is_usable(formula: FloatingCouponFormula) -> bool:
    return formula.status == VersionedStatus.ACTIVE and formula.data_quality_status != FormulaDataQuality.UNKNOWN


def _estimate_coupon_period_days(coupons, index: int) -> int | None:
    current = coupons[index].coupon_date
    if index > 0:
        return (current - coupons[index - 1].coupon_date).days
    if index + 1 < len(coupons):
        return (coupons[index + 1].coupon_date - current).days
    return None


def _annual_rate(index_rate: Decimal, spread_bps: int, floor_rate_bps: int | None, cap_rate_bps: int | None) -> Decimal:
    value = index_rate + Decimal(spread_bps) / Decimal("100")
    if floor_rate_bps is not None:
        value = max(value, Decimal(floor_rate_bps) / Decimal("100"))
    if cap_rate_bps is not None:
        value = min(value, Decimal(cap_rate_bps) / Decimal("100"))
    return value


def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"
