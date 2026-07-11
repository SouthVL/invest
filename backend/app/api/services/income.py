from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from app.analytics.cashflow_forecast import _add_months, build_monthly_cashflow
from app.domain.cashflow import CashflowEvent, CashflowType
from app.reporting.cashflow import CashflowReport, is_capital_return, source_status
from app.reporting.serializers.cashflow_json import decimal_text, iso_datetime, money

IncomeType = Literal["all", "coupon", "dividend"]
IncomeStatus = Literal["all", "confirmed", "forecast"]


def build_income_response(
    *,
    report: CashflowReport,
    period_label: str,
    income_type: IncomeType,
    status: IncomeStatus,
) -> dict[str, Any]:
    events = filtered_income_events(report, income_type=income_type, status=status)
    monthly_rows = build_monthly_cashflow(events, start_date=report.as_of, months=report.months, currency=report.report_currency)
    coupon_total = sum((event.total_amount for event in events if event.event_type == CashflowType.COUPON), Decimal("0"))
    dividend_total = sum((event.total_amount for event in events if event.event_type == CashflowType.DIVIDEND), Decimal("0"))
    confirmed_total = sum((event.total_amount for event in events if income_status(event) == "confirmed"), Decimal("0"))
    forecast_total = sum((event.total_amount for event in events if income_status(event) == "forecast"), Decimal("0"))
    nearest_payment = min(events, key=lambda event: event.event_date, default=None)

    return {
        "schema_version": report.schema_version,
        "report_type": "income",
        "generated_at": iso_datetime(report.generated_at),
        "period": {
            "label": period_label,
            "from": report.as_of.isoformat(),
            "to": _add_months(report.as_of, report.months).isoformat(),
            "months": report.months,
        },
        "currency": report.report_currency,
        "filters": {
            "type": income_type,
            "status": status,
        },
        "summary": {
            "total": money(coupon_total + dividend_total, report.report_currency),
            "coupons": money(coupon_total, report.report_currency),
            "dividends": money(dividend_total, report.report_currency),
            "confirmed": money(confirmed_total, report.report_currency),
            "forecast": money(forecast_total, report.report_currency),
            "payments_count": len(events),
            "nearest_payment": income_event_to_dict(nearest_payment, report.report_currency) if nearest_payment else None,
        },
        "monthly": [
            {
                "month": row.month,
                "coupons": money(row.coupons, row.currency),
                "dividends": money(row.dividends, row.currency),
                "confirmed": money(monthly_total(events, row.month, "confirmed"), row.currency),
                "forecast": money(monthly_total(events, row.month, "forecast"), row.currency),
                "total": money(row.coupons + row.dividends, row.currency),
            }
            for row in monthly_rows
        ],
        "payments": [income_event_to_dict(event, report.report_currency) for event in sorted(events, key=lambda event: event.event_date)],
        "warnings": income_warnings(report),
        "data_quality": report.data_quality,
    }


def filtered_income_events(report: CashflowReport, *, income_type: IncomeType, status: IncomeStatus) -> list[CashflowEvent]:
    events = [event for account in report.accounts for event in account.events if not is_capital_return(event.event_type)]
    if income_type != "all":
        expected_type = CashflowType.COUPON if income_type == "coupon" else CashflowType.DIVIDEND
        events = [event for event in events if event.event_type == expected_type]
    if status != "all":
        events = [event for event in events if income_status(event) == status]
    return events


def income_status(event: CashflowEvent) -> Literal["confirmed", "forecast"]:
    return "forecast" if source_status(event.source) == "estimated" else "confirmed"


def monthly_total(events: list[CashflowEvent], month: str, status: IncomeStatus) -> Decimal:
    return sum(
        (
            event.total_amount
            for event in events
            if f"{event.event_date.year:04d}-{event.event_date.month:02d}" == month and income_status(event) == status
        ),
        Decimal("0"),
    )


def income_event_to_dict(event: CashflowEvent | None, currency: str) -> dict[str, Any] | None:
    if event is None:
        return None
    payment_currency = event.payment_currency or event.currency or currency
    payment_amount = event.payment_amount_per_unit if event.payment_amount_per_unit is not None else event.amount_per_bond
    payment_total = event.payment_total_amount if event.payment_total_amount is not None else event.total_amount
    return {
        "instrument_uid": event.instrument_uid,
        "instrument_name": event.name,
        "figi": event.figi,
        "isin": event.isin,
        "payment_date": event.event_date.isoformat(),
        "payment_month": f"{event.event_date.year:04d}-{event.event_date.month:02d}",
        "income_type": event.event_type.value,
        "status": income_status(event),
        "amount_per_unit": money(event.amount_per_bond, event.currency),
        "payment_amount_per_unit": money(payment_amount, payment_currency),
        "quantity": decimal_text(event.quantity),
        "total": money(event.total_amount, event.currency),
        "payment_total": money(payment_total, payment_currency),
        "currency": event.currency.upper(),
        "source": event.source.value,
    }


def income_warnings(report: CashflowReport) -> list[str]:
    warnings = [warning for warning in report.warnings if "maturit" not in warning.lower() and "amortization" not in warning.lower()]
    warnings.append("Income excludes amortizations, maturities and offer redemptions because they are capital return, not income.")
    return warnings
