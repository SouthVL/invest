from __future__ import annotations

import argparse

import app.cli as legacy_cli
from rich.console import Console

from app.application.offers import OffersRequest, build_t_invest_offers_report
from app.interfaces.cli.commands._adapter import add_flag, add_option
from app.interfaces.cli.commands.cashflow import write_or_print
from app.reporting.serializers.offers_json import offers_report_to_json


def run(args: argparse.Namespace) -> int:
    if args.format == "json":
        console = Console()
        try:
            report = build_t_invest_offers_report(
                OffersRequest(
                    account_id=args.account_id,
                    as_of=args.as_of,
                    days=args.days,
                    warning_days=args.warning_days,
                    include_account_id=args.include_account_id,
                )
            )
        except Exception as exc:
            console.print(f"[red]{exc}[/red]")
            return 1
        return write_or_print(offers_report_to_json(report), args.output)

    argv = ["offers"]
    add_option(argv, "--account-id", args.account_id)
    add_option(argv, "--days", args.days)
    add_option(argv, "--warning-days", args.warning_days)
    add_flag(argv, "--details", args.details)
    add_option(argv, "--as-of", args.as_of)
    return legacy_cli.main(argv)
