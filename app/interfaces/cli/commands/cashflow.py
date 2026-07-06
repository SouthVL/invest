from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from app.application.cashflow import CashflowRequest, build_t_invest_cashflow_report
from app.reporting.renderers.cashflow_table import render_cashflow_report
from app.reporting.serializers.cashflow_csv import cashflow_events_to_csv, cashflow_monthly_to_csv
from app.reporting.serializers.cashflow_json import cashflow_report_to_json


def run(args: argparse.Namespace) -> int:
    console = Console()
    try:
        report = build_t_invest_cashflow_report(
            CashflowRequest(
                account_id=args.account_id,
                months=args.months,
                as_of=args.as_of,
                report_currency=args.currency,
                repeat_floating_last_coupon=args.repeat_floating_last_coupon,
                include_account_id=args.include_account_id,
            )
        )
    except Exception as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    if args.format == "table":
        render_cashflow_report(report, console)
        return 0
    if args.format == "json":
        return write_or_print(cashflow_report_to_json(report), args.output)
    if args.format == "csv":
        return write_cashflow_csv(report, args.output, console)
    console.print(f"[red]Unsupported format: {args.format}[/red]")
    return 2


def write_or_print(text: str, output: Path | None) -> int:
    if output is None:
        print(text, end="")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    return 0


def write_cashflow_csv(report, output: Path | None, console: Console) -> int:
    monthly_csv = cashflow_monthly_to_csv(report)
    events_csv = cashflow_events_to_csv(report)
    if output is None:
        print(monthly_csv, end="")
        return 0
    if output.suffix.lower() == ".csv":
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(monthly_csv, encoding="utf-8")
        return 0

    output.mkdir(parents=True, exist_ok=True)
    (output / "cashflow_monthly.csv").write_text(monthly_csv, encoding="utf-8")
    (output / "cashflow_events.csv").write_text(events_csv, encoding="utf-8")
    console.print(f"Wrote cashflow CSV files to {output}")
    return 0
