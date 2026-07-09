from __future__ import annotations

import argparse
from datetime import datetime, timezone

from rich.console import Console

from app.application.cashflow import CashflowRequest, build_t_invest_cashflow_report
from app.application.offers import OffersRequest, build_t_invest_offers_report
from app.application.portfolio import PortfolioRequest, build_t_invest_portfolio_report
from app.demo.provider import build_demo_cashflow_report, build_demo_offers_report, build_demo_portfolio_report
from app.reporting.report_package import write_report_package


def run(args: argparse.Namespace) -> int:
    console = Console()
    try:
        generated_at = datetime.now(timezone.utc)
        offer_days = args.offer_days if args.offer_days is not None else args.months * 31
        include_account_id = bool(args.include_account_id and not args.anonymize)
        cashflow_report = build_t_invest_cashflow_report(
            CashflowRequest(
                months=args.months,
                as_of=args.as_of,
                account_id=args.account_id,
                report_currency=args.currency,
                repeat_floating_last_coupon=args.repeat_floating_last_coupon,
                include_account_id=include_account_id,
                generated_at=generated_at,
            )
        )
        offers_report = build_t_invest_offers_report(
            OffersRequest(
                as_of=args.as_of,
                days=offer_days,
                warning_days=args.warning_days,
                account_id=args.account_id,
                include_account_id=include_account_id,
                generated_at=generated_at,
            )
        )
        portfolio_report = build_t_invest_portfolio_report(
            PortfolioRequest(
                as_of=args.as_of,
                account_id=args.account_id,
                include_account_id=include_account_id,
                generated_at=generated_at,
            )
        )
        package = write_report_package(
            output_dir=args.output,
            cashflow_report=cashflow_report,
            offers_report=offers_report,
            portfolio_report=portfolio_report,
            mode="t-invest",
            scenario=args.scenario,
            anonymize=args.anonymize,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    console.print(f"Report written to {package.output_dir}")
    console.print(f"Manifest: {package.output_dir / 'manifest.json'}")
    return 0


def run_demo(args: argparse.Namespace) -> int:
    console = Console()
    try:
        offer_days = args.offer_days if args.offer_days is not None else args.months * 31
        cashflow_report = build_demo_cashflow_report(
            months=args.months,
            as_of=args.as_of,
            report_currency=args.currency,
        )
        offers_report = build_demo_offers_report(
            as_of=args.as_of,
            days=offer_days,
            warning_days=args.warning_days,
        )
        portfolio_report = build_demo_portfolio_report(as_of=args.as_of)
        package = write_report_package(
            output_dir=args.output,
            cashflow_report=cashflow_report,
            offers_report=offers_report,
            portfolio_report=portfolio_report,
            mode="demo",
            scenario=args.scenario,
            anonymize=args.anonymize,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    console.print(f"Demo report written to {package.output_dir}")
    console.print(f"Manifest: {package.output_dir / 'manifest.json'}")
    return 0
