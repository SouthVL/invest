from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.cli import parse_cli_date
from app.demo.provider import DEMO_AS_OF


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cooperative South Finance Lab portfolio analytics tools.")
    subparsers = parser.add_subparsers(dest="command")

    _add_cashflow(subparsers)
    _add_portfolio(subparsers)
    _add_floaters(subparsers)
    _add_offers(subparsers)
    _add_demo(subparsers)
    _add_legacy_aliases(subparsers)
    return parser


def _add_cashflow(subparsers: argparse._SubParsersAction) -> None:
    cashflow = subparsers.add_parser("cashflow", help="Show monthly portfolio cashflow forecast.")
    cashflow.set_defaults(handler="cashflow")
    cashflow.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    cashflow.add_argument("--months", type=int, default=12, help="Number of forecast months.")
    cashflow.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Forecast start date as DD.MM.YYYY.")
    cashflow.add_argument("--currency", default="RUB", help="Report currency. Defaults to RUB.")
    cashflow.add_argument("--format", choices=["table", "json", "csv"], default="table", help="Output format.")
    cashflow.add_argument("--output", type=Path, help="Output file or directory.")
    cashflow.add_argument("--include-account-id", action="store_true", help="Include real T-Invest account IDs in machine-readable output.")
    cashflow.add_argument(
        "--repeat-floating-last-coupon",
        action="store_true",
        help="For floating-rate bonds, use the last known coupon amount when a future coupon amount is missing.",
    )


def _add_portfolio(subparsers: argparse._SubParsersAction) -> None:
    portfolio = subparsers.add_parser("portfolio", help="Portfolio commands.")
    portfolio_subparsers = portfolio.add_subparsers(dest="portfolio_command", required=True)

    snapshot = portfolio_subparsers.add_parser("snapshot", help="Fetch and store the full current portfolio.")
    snapshot.set_defaults(handler="portfolio_snapshot")
    snapshot.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    snapshot.add_argument("--db-path", default="invest.db", help="SQLite path. Defaults to invest.db.")
    snapshot.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Snapshot date as DD.MM.YYYY.")


def _add_floaters(subparsers: argparse._SubParsersAction) -> None:
    floaters = subparsers.add_parser("floaters", help="Floating-rate bond commands.")
    floater_subparsers = floaters.add_subparsers(dest="floaters_command", required=True)

    forecast = floater_subparsers.add_parser("forecast", help="Show floating coupon forecast.")
    forecast.set_defaults(handler="floaters_forecast")
    forecast.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    forecast.add_argument("--months", type=int, default=12, help="Number of forecast months.")
    forecast.add_argument("--scenario", default="base", help="Scenario name from rate_scenarios.yaml.")
    forecast.add_argument("--formulas", default="app/data/floating_coupon_formulas.yaml", help="Floating coupon formulas YAML path.")
    forecast.add_argument("--scenarios", default="app/data/rate_scenarios.yaml", help="Interest-rate scenarios YAML path.")
    forecast.add_argument("--only-unknown", action="store_true", help="Show only unknown events in the detailed table.")
    forecast.add_argument("--details", action="store_true", help="Accepted for compatibility; details are shown by default.")
    forecast.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Forecast start date as DD.MM.YYYY.")
    forecast.add_argument("--currency", default="RUB", help="Display currency label. Defaults to RUB.")

    scenarios = floater_subparsers.add_parser("scenarios", help="Show simplified floating coupon scenarios.")
    scenarios.set_defaults(handler="floaters_scenarios")
    scenarios.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    scenarios.add_argument("--months", type=int, default=12, help="Number of forecast months.")
    scenarios.add_argument("--delta-percent", type=Decimal, default=Decimal("1.0"), help="Rate delta in percentage points.")
    scenarios.add_argument("--details", action="store_true", help="Show detailed bond/date scenario rows.")
    scenarios.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Forecast start date as DD.MM.YYYY.")


def _add_offers(subparsers: argparse._SubParsersAction) -> None:
    offers = subparsers.add_parser("offers", help="Show upcoming bond offers.")
    offers.set_defaults(handler="offers")
    offers.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    offers.add_argument("--days", type=int, default=180, help="Show offers within this many days.")
    offers.add_argument("--warning-days", type=int, default=45, help="Mark offers within this many days as WARNING.")
    offers.add_argument("--details", action="store_true", help="Accepted for compatibility; main table is always shown.")
    offers.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Start date as DD.MM.YYYY.")
    offers.add_argument("--format", choices=["table", "json"], default="table", help="Output format.")
    offers.add_argument("--output", type=Path, help="Output file.")
    offers.add_argument("--include-account-id", action="store_true", help="Include real T-Invest account IDs in machine-readable output.")


def _add_demo(subparsers: argparse._SubParsersAction) -> None:
    demo = subparsers.add_parser("demo", help="Offline demo commands.")
    demo_subparsers = demo.add_subparsers(dest="demo_command", required=True)

    cashflow = demo_subparsers.add_parser("cashflow", help="Show deterministic demo cashflow without token or network.")
    cashflow.set_defaults(handler="demo_cashflow")
    cashflow.add_argument("--months", type=int, default=12, help="Number of forecast months.")
    cashflow.add_argument("--as-of", type=parse_cli_date, default=DEMO_AS_OF, help="Forecast start date as DD.MM.YYYY.")
    cashflow.add_argument("--currency", default="RUB", help="Report currency. Defaults to RUB.")
    cashflow.add_argument("--format", choices=["table", "json", "csv"], default="table", help="Output format.")
    cashflow.add_argument("--output", type=Path, help="Output file or directory.")


def _add_legacy_aliases(subparsers: argparse._SubParsersAction) -> None:
    portfolio_all = subparsers.add_parser("portfolio-all", help="Legacy alias for 'portfolio snapshot'.")
    portfolio_all.set_defaults(handler="portfolio_snapshot")
    portfolio_all.add_argument("--account-id")
    portfolio_all.add_argument("--db-path", default="invest.db")
    portfolio_all.add_argument("--as-of", type=parse_cli_date)

    floating = subparsers.add_parser("floating-forecast", help="Legacy alias for 'floaters forecast'.")
    floating.set_defaults(handler="floaters_forecast")
    floating.add_argument("--account-id")
    floating.add_argument("--months", type=int, default=12)
    floating.add_argument("--scenario", default="base")
    floating.add_argument("--formulas", default="app/data/floating_coupon_formulas.yaml")
    floating.add_argument("--scenarios", default="app/data/rate_scenarios.yaml")
    floating.add_argument("--only-unknown", action="store_true")
    floating.add_argument("--details", action="store_true")
    floating.add_argument("--as-of", type=parse_cli_date)
    floating.add_argument("--currency", default="RUB")

    scenarios = subparsers.add_parser("floating-scenarios", help="Legacy alias for 'floaters scenarios'.")
    scenarios.set_defaults(handler="floaters_scenarios")
    scenarios.add_argument("--account-id")
    scenarios.add_argument("--months", type=int, default=12)
    scenarios.add_argument("--delta-percent", type=Decimal, default=Decimal("1.0"))
    scenarios.add_argument("--details", action="store_true")
    scenarios.add_argument("--as-of", type=parse_cli_date)
