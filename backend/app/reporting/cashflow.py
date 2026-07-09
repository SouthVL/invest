from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType, MonthlyCashflow

SCHEMA_VERSION = "1.0"


class CashflowSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    fixed_coupons: Decimal = Decimal("0")
    floating_coupons: Decimal = Decimal("0")
    dividends: Decimal = Decimal("0")
    amortizations: Decimal = Decimal("0")
    maturities: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    actual_total: Decimal = Decimal("0")
    estimated_total: Decimal = Decimal("0")
    unknown_count: int = 0
    currency: str = "RUB"


class CashflowAccountReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_label: str
    account_id: str | None = None
    monthly: list[MonthlyCashflow] = Field(default_factory=list)
    events: list[CashflowEvent] = Field(default_factory=list)


class CashflowReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = SCHEMA_VERSION
    report_type: str = "cashflow"
    generated_at: datetime
    as_of: date
    months: int
    report_currency: str
    accounts: list[CashflowAccountReport]
    summary: CashflowSummary
    warnings: list[str] = Field(default_factory=list)
    data_quality: dict[str, Any] = Field(default_factory=dict)


def build_cashflow_report(
    *,
    as_of: date,
    months: int,
    report_currency: str,
    account_results: list[CashflowAccountReport],
    generated_at: datetime | None = None,
) -> CashflowReport:
    summary = summarize_cashflow(account_results, currency=report_currency)
    warnings = []
    if summary.estimated_total > Decimal("0"):
        warnings.append("Some cashflow items are estimates and are not confirmed payments.")
    if summary.unknown_count:
        warnings.append("Some cashflow items have unknown values.")

    return CashflowReport(
        generated_at=generated_at or datetime.now(timezone.utc),
        as_of=as_of,
        months=months,
        report_currency=report_currency.upper(),
        accounts=account_results,
        summary=summary,
        warnings=warnings,
        data_quality={
            "account_count": len(account_results),
            "event_count": sum(len(account.events) for account in account_results),
            "source_statuses": sorted({source_status(event.source) for account in account_results for event in account.events}),
        },
    )


def summarize_cashflow(account_results: list[CashflowAccountReport], *, currency: str) -> CashflowSummary:
    fixed_coupons = Decimal("0")
    floating_coupons = Decimal("0")
    dividends = Decimal("0")
    amortizations = Decimal("0")
    maturities = Decimal("0")
    actual_total = Decimal("0")
    estimated_total = Decimal("0")

    for account in account_results:
        for row in account.monthly:
            fixed_coupons += row.fixed_coupons
            floating_coupons += row.floating_coupons
            dividends += row.dividends
            amortizations += row.amortizations
            maturities += row.maturities
        for event in account.events:
            if source_status(event.source) == "estimated":
                estimated_total += event.total_amount
            elif source_status(event.source) == "actual":
                actual_total += event.total_amount

    total = fixed_coupons + floating_coupons + dividends + amortizations + maturities
    return CashflowSummary(
        fixed_coupons=fixed_coupons,
        floating_coupons=floating_coupons,
        dividends=dividends,
        amortizations=amortizations,
        maturities=maturities,
        total=total,
        actual_total=actual_total,
        estimated_total=estimated_total,
        currency=currency.upper(),
    )


def combine_monthly_rows(account_results: list[CashflowAccountReport], *, currency: str) -> list[MonthlyCashflow]:
    if not account_results:
        return []

    month_order: list[str] = []
    totals: dict[str, dict[str, Decimal]] = {}
    for account in account_results:
        for row in account.monthly:
            if row.month not in totals:
                month_order.append(row.month)
                totals[row.month] = {
                    "coupons": Decimal("0"),
                    "fixed_coupons": Decimal("0"),
                    "floating_coupons": Decimal("0"),
                    "dividends": Decimal("0"),
                    "amortizations": Decimal("0"),
                    "maturities": Decimal("0"),
                }
            totals[row.month]["coupons"] += row.coupons
            totals[row.month]["fixed_coupons"] += row.fixed_coupons
            totals[row.month]["floating_coupons"] += row.floating_coupons
            totals[row.month]["dividends"] += row.dividends
            totals[row.month]["amortizations"] += row.amortizations
            totals[row.month]["maturities"] += row.maturities

    rows = []
    for month in sorted(month_order):
        values = totals[month]
        total = values["coupons"] + values["dividends"] + values["amortizations"] + values["maturities"]
        rows.append(
            MonthlyCashflow(
                month=month,
                coupons=values["coupons"],
                fixed_coupons=values["fixed_coupons"],
                floating_coupons=values["floating_coupons"],
                dividends=values["dividends"],
                amortizations=values["amortizations"],
                maturities=values["maturities"],
                total=total,
                currency=currency.upper(),
            )
        )
    return rows


def source_status(source: CashflowSource) -> str:
    if source == CashflowSource.REPEATED_FLOATING_COUPON:
        return "estimated"
    return "actual"


def event_assumptions(event: CashflowEvent) -> list[str]:
    if event.source == CashflowSource.REPEATED_FLOATING_COUPON:
        return ["Floating coupon amount is repeated from the last known coupon."]
    return []


def event_source_label(event: CashflowEvent) -> str:
    if event.source == CashflowSource.FLOATING_COUPON:
        return "floating"
    if event.source == CashflowSource.REPEATED_FLOATING_COUPON:
        return "floating: last coupon"
    return event.source.value


def is_capital_return(event_type: CashflowType) -> bool:
    return event_type in {CashflowType.AMORTIZATION, CashflowType.MATURITY}
