from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType, MonthlyCashflow


def build_monthly_cashflow(
    events: list[CashflowEvent],
    start_date: date,
    months: int,
    currency: str = "RUB",
) -> list[MonthlyCashflow]:
    """
    Groups cashflow events by month.

    Include events where:
    start_date <= event_date < first_day_after_forecast_window

    Return exactly months rows, even if some months have zero cashflow.
    """
    if months < 1:
        raise ValueError("months must be at least 1")

    start_month = date(start_date.year, start_date.month, 1)
    month_keys = [_month_key(_add_months(start_month, offset)) for offset in range(months)]
    window_end = _add_months(start_month, months)
    buckets = {
        month: {
            "fixed_coupons": Decimal("0"),
            "floating_coupons": Decimal("0"),
            CashflowType.COUPON: Decimal("0"),
            CashflowType.DIVIDEND: Decimal("0"),
            CashflowType.AMORTIZATION: Decimal("0"),
            CashflowType.MATURITY: Decimal("0"),
        }
        for month in month_keys
    }

    for event in events:
        if event.event_date < start_date or event.event_date >= window_end:
            continue
        month = _month_key(event.event_date)
        if month not in buckets:
            continue
        buckets[month][event.event_type] += event.total_amount
        if event.event_type == CashflowType.COUPON:
            if event.source == CashflowSource.ACTUAL:
                buckets[month]["fixed_coupons"] += event.total_amount
            else:
                buckets[month]["floating_coupons"] += event.total_amount

    rows: list[MonthlyCashflow] = []
    for month in month_keys:
        fixed_coupons = buckets[month]["fixed_coupons"]
        floating_coupons = buckets[month]["floating_coupons"]
        coupons = fixed_coupons + floating_coupons
        dividends = buckets[month][CashflowType.DIVIDEND]
        amortizations = buckets[month][CashflowType.AMORTIZATION]
        maturities = buckets[month][CashflowType.MATURITY]
        rows.append(
            MonthlyCashflow(
                month=month,
                coupons=coupons,
                fixed_coupons=fixed_coupons,
                floating_coupons=floating_coupons,
                dividends=dividends,
                amortizations=amortizations,
                maturities=maturities,
                total=coupons + dividends + amortizations + maturities,
                currency=currency,
            )
        )
    return rows


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"
