from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.domain.cashflow import CashflowEvent
from app.reporting.cashflow import CashflowReport, event_assumptions, event_source_label, is_capital_return, source_status


def cashflow_report_to_dict(report: CashflowReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "report_type": report.report_type,
        "generated_at": iso_datetime(report.generated_at),
        "as_of": report.as_of.isoformat(),
        "months": report.months,
        "report_currency": report.report_currency,
        "accounts": [
            {
                "account_label": account.account_label,
                **({"account_id": account.account_id} if account.account_id else {}),
                "monthly": [
                    {
                        "month": row.month,
                        "fixed_coupons": money(row.fixed_coupons, row.currency),
                        "floating_coupons": money(row.floating_coupons, row.currency),
                        "dividends": money(row.dividends, row.currency),
                        "amortizations": money(row.amortizations, row.currency),
                        "maturities": money(row.maturities, row.currency),
                        "total": money(row.total, row.currency),
                    }
                    for row in account.monthly
                ],
                "events": [event_to_dict(event) for event in account.events],
            }
            for account in report.accounts
        ],
        "summary": {
            "fixed_coupons": money(report.summary.fixed_coupons, report.summary.currency),
            "floating_coupons": money(report.summary.floating_coupons, report.summary.currency),
            "dividends": money(report.summary.dividends, report.summary.currency),
            "amortizations": money(report.summary.amortizations, report.summary.currency),
            "maturities": money(report.summary.maturities, report.summary.currency),
            "total": money(report.summary.total, report.summary.currency),
            "actual_total": money(report.summary.actual_total, report.summary.currency),
            "estimated_total": money(report.summary.estimated_total, report.summary.currency),
            "unknown_count": report.summary.unknown_count,
        },
        "warnings": report.warnings,
        "data_quality": report.data_quality,
    }


def cashflow_report_to_json(report: CashflowReport) -> str:
    return json.dumps(cashflow_report_to_dict(report), ensure_ascii=False, indent=2) + "\n"


def event_to_dict(event: CashflowEvent) -> dict[str, Any]:
    payment_currency = event.payment_currency or event.currency
    payment_amount = event.payment_amount_per_unit if event.payment_amount_per_unit is not None else event.amount_per_bond
    payment_total = event.payment_total_amount if event.payment_total_amount is not None else event.total_amount
    return {
        "instrument_name": event.name,
        "figi": event.figi,
        "isin": event.isin,
        "payment_date": event.event_date.isoformat(),
        "payment_month": f"{event.event_date.year:04d}-{event.event_date.month:02d}",
        "payment_type": event.event_type.value,
        "amount_per_unit": money(event.amount_per_bond, event.currency),
        "payment_amount_per_unit": money(payment_amount, payment_currency),
        "quantity": decimal_text(event.quantity),
        "total": money(event.total_amount, event.currency),
        "payment_total": money(payment_total, payment_currency),
        "source": event_source_label(event),
        "source_status": source_status(event.source),
        "scenario_id": None,
        "assumptions": event_assumptions(event),
        "is_capital_return": is_capital_return(event.event_type),
    }


def money(amount: Decimal, currency: str) -> dict[str, str]:
    return {"amount": decimal_text(amount), "currency": currency.upper()}


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def iso_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
