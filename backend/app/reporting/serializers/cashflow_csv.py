from __future__ import annotations

import csv
from io import StringIO

from app.domain.cashflow import CashflowEvent, MonthlyCashflow
from app.reporting.cashflow import CashflowReport, event_source_label, is_capital_return, source_status
from app.reporting.serializers.cashflow_json import decimal_text

MONTHLY_HEADER = [
    "account_label",
    "month",
    "fixed_coupons_amount",
    "floating_coupons_amount",
    "dividends_amount",
    "amortizations_amount",
    "maturities_amount",
    "total_amount",
    "currency",
]

EVENTS_HEADER = [
    "account_label",
    "payment_date",
    "payment_month",
    "payment_type",
    "instrument_name",
    "isin",
    "figi",
    "quantity",
    "amount_per_unit",
    "total_amount",
    "currency",
    "payment_amount_per_unit",
    "payment_total_amount",
    "payment_currency",
    "source",
    "source_status",
    "scenario_id",
    "is_capital_return",
]


def cashflow_monthly_to_csv(report: CashflowReport) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(MONTHLY_HEADER)
    for account in report.accounts:
        for row in account.monthly:
            writer.writerow(monthly_row(account.account_label, row))
    return output.getvalue()


def cashflow_events_to_csv(report: CashflowReport) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(EVENTS_HEADER)
    for account in report.accounts:
        for event in account.events:
            writer.writerow(event_row(account.account_label, event))
    return output.getvalue()


def monthly_row(account_label: str, row: MonthlyCashflow) -> list[str]:
    return [
        account_label,
        row.month,
        decimal_text(row.fixed_coupons),
        decimal_text(row.floating_coupons),
        decimal_text(row.dividends),
        decimal_text(row.amortizations),
        decimal_text(row.maturities),
        decimal_text(row.total),
        row.currency.upper(),
    ]


def event_row(account_label: str, event: CashflowEvent) -> list[str]:
    payment_currency = event.payment_currency or event.currency
    payment_amount = event.payment_amount_per_unit if event.payment_amount_per_unit is not None else event.amount_per_bond
    payment_total = event.payment_total_amount if event.payment_total_amount is not None else event.total_amount
    return [
        account_label,
        event.event_date.isoformat(),
        f"{event.event_date.year:04d}-{event.event_date.month:02d}",
        event.event_type.value,
        event.name,
        event.isin or "",
        event.figi or "",
        decimal_text(event.quantity),
        decimal_text(event.amount_per_bond),
        decimal_text(event.total_amount),
        event.currency.upper(),
        decimal_text(payment_amount),
        decimal_text(payment_total),
        payment_currency.upper(),
        event_source_label(event),
        source_status(event.source),
        "",
        "true" if is_capital_return(event.event_type) else "false",
    ]
