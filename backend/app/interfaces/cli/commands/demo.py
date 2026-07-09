from __future__ import annotations

import argparse

from rich.console import Console

from app.demo.provider import build_demo_cashflow_report
from app.interfaces.cli.commands.cashflow import write_cashflow_csv, write_or_print
from app.reporting.renderers.cashflow_table import render_cashflow_report
from app.reporting.serializers.cashflow_json import cashflow_report_to_json


def run_cashflow(args: argparse.Namespace) -> int:
    console = Console()
    try:
        report = build_demo_cashflow_report(
            months=args.months,
            as_of=args.as_of,
            report_currency=args.currency,
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
