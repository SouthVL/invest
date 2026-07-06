from __future__ import annotations

from rich.console import Console

from app.cli import render_cashflow, render_cashflow_details, render_maturity_details
from app.reporting.cashflow import CashflowReport, combine_monthly_rows


def render_cashflow_report(report: CashflowReport, console: Console) -> None:
    for account in report.accounts:
        render_cashflow_details(
            account.events,
            console,
            start_date=report.as_of,
            months=report.months,
            title=f"Future portfolio cashflow details - {account.account_label}",
        )
        render_cashflow(
            account.monthly,
            console,
            title=f"Monthly portfolio cashflow forecast - {account.account_label}",
        )
        render_maturity_details(account.events, console, title=f"Maturity details - {account.account_label}")

    if len(report.accounts) > 1:
        render_cashflow(
            combine_monthly_rows(report.accounts, currency=report.report_currency),
            console,
            title="Monthly portfolio cashflow forecast - All accounts total",
        )
