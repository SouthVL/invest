from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from rich import box
from rich.console import Console
from rich.table import Table

from app.analytics.bond_offers import offer_summary_counts
from app.analytics.floating_coupon_forecast import (
    aggregate_monthly_floating_forecast,
    build_floating_coupon_forecast,
)
from app.analytics.floating_scenarios import (
    aggregate_monthly_scenarios,
    build_floating_scenario_forecast,
)
from app.analytics.cashflow_forecast import _add_months, build_monthly_cashflow
from app.config.floating_coupon_loader import load_floating_coupon_formulas, load_rate_scenario
from app.domain.bond_offer import BondOfferEvent, OfferStatus
from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType, MonthlyCashflow
from app.domain.floating_coupon import (
    CouponForecastSource,
    FloatingCouponForecastEvent,
    MonthlyFloatingCouponForecast,
)
from app.domain.floating_scenarios import (
    FloatingScenarioCouponEvent,
    MonthlyScenarioForecast,
    ScenarioType,
)
from app.domain.portfolio_all import PortfolioAsset, PortfolioSnapshot
from app.storage.portfolio_all import PortfolioAllRepository
from app.t_invest.cashflow import TInvestCashflowService
from app.t_invest.bond_offers import TInvestBondOfferService
from app.t_invest.floating_bonds import TInvestFloatingBondService
from app.t_invest.floating_scenarios import TInvestFloatingScenarioService
from app.t_invest.portfolio_all import TInvestPortfolioAllService
from invest_bonds.cli import account_title, main as portfolio_main, select_accounts
from invest_bonds.config import ConfigError, load_settings
from invest_bonds.models import AccountSummary
from invest_bonds.sdk_compat import configure_t_invest_sdk


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0].startswith("-") and argv[0] not in {"-h", "--help"}):
        return portfolio_main(argv)

    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()

    if args.command == "cashflow":
        return cashflow_command(args, console)
    if args.command == "floating-forecast":
        return floating_forecast_command(args, console)
    if args.command == "floating-scenarios":
        return floating_scenarios_command(args, console)
    if args.command == "offers":
        return offers_command(args, console)
    if args.command == "portfolio-all":
        return portfolio_all_command(args, console)

    return portfolio_main(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cooperative South Finance Lab portfolio analytics tools.")
    subparsers = parser.add_subparsers(dest="command")

    cashflow = subparsers.add_parser("cashflow", help="Show monthly portfolio cashflow forecast.")
    cashflow.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    cashflow.add_argument("--months", type=int, default=12, help="Number of forecast months.")
    cashflow.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Forecast start date as DD.MM.YYYY.")
    cashflow.add_argument("--currency", default="RUB", help="Display currency label. Defaults to RUB.")
    cashflow.add_argument(
        "--repeat-floating-last-coupon",
        action="store_true",
        help="For floating-rate bonds, use the last known coupon amount when a future coupon amount is missing.",
    )

    floating = subparsers.add_parser("floating-forecast", help="Show floating coupon forecast.")
    floating.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    floating.add_argument("--months", type=int, default=12, help="Number of forecast months.")
    floating.add_argument("--scenario", default="base", help="Scenario name from rate_scenarios.yaml.")
    floating.add_argument("--formulas", default="app/data/floating_coupon_formulas.yaml", help="Floating coupon formulas YAML path.")
    floating.add_argument("--scenarios", default="app/data/rate_scenarios.yaml", help="Interest-rate scenarios YAML path.")
    floating.add_argument("--only-unknown", action="store_true", help="Show only unknown events in the detailed table.")
    floating.add_argument("--details", action="store_true", help="Accepted for compatibility; details are shown by default.")
    floating.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Forecast start date as DD.MM.YYYY.")
    floating.add_argument("--currency", default="RUB", help="Display currency label. Defaults to RUB.")

    scenarios = subparsers.add_parser("floating-scenarios", help="Show simplified floating coupon scenarios.")
    scenarios.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    scenarios.add_argument("--months", type=int, default=12, help="Number of forecast months.")
    scenarios.add_argument("--delta-percent", type=Decimal, default=Decimal("1.0"), help="Rate delta in percentage points.")
    scenarios.add_argument("--details", action="store_true", help="Show detailed bond/date scenario rows.")
    scenarios.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Forecast start date as DD.MM.YYYY.")

    offers = subparsers.add_parser("offers", help="Show upcoming bond offers.")
    offers.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    offers.add_argument("--days", type=int, default=180, help="Show offers within this many days.")
    offers.add_argument("--warning-days", type=int, default=45, help="Mark offers within this many days as WARNING.")
    offers.add_argument("--details", action="store_true", help="Accepted for compatibility; main table is always shown.")
    offers.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Start date as DD.MM.YYYY.")

    portfolio_all = subparsers.add_parser("portfolio-all", help="Fetch and store the full current portfolio.")
    portfolio_all.add_argument("--account-id", help="T-Invest account id to fetch. If omitted, all accounts are processed.")
    portfolio_all.add_argument("--db-path", default="invest.db", help="SQLite path. Defaults to invest.db.")
    portfolio_all.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Snapshot date as DD.MM.YYYY.")
    return parser


def cashflow_command(args: argparse.Namespace, console: Console) -> int:
    if args.months < 1:
        console.print("[red]--months must be at least 1[/red]")
        return 2

    try:
        settings = load_settings()
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    configure_t_invest_sdk()
    from t_tech.invest import Client

    start_date = args.as_of
    to_date = _add_months(date(start_date.year, start_date.month, 1), args.months)
    with Client(settings.invest_token) as client:
        accounts = [
            AccountSummary(
                id=account.id,
                name=getattr(account, "name", ""),
                type=str(getattr(account, "type", "")),
                status=str(getattr(account, "status", "")),
                access_level=str(getattr(account, "access_level", "")),
            )
            for account in client.users.get_accounts().accounts
        ]
        selected_accounts = select_accounts(args.account_id, accounts, console)
        if not selected_accounts:
            return 2

        service = TInvestCashflowService(client)
        account_rows: list[list[MonthlyCashflow]] = []
        for account in selected_accounts:
            events = service.get_portfolio_cashflow_events(
                account_id=account.id,
                from_date=start_date,
                to_date=to_date,
                repeat_floating_last_coupon=args.repeat_floating_last_coupon,
                report_currency=args.currency.upper(),
            )
            if not events:
                continue
            rows = build_monthly_cashflow(
                events,
                start_date=start_date,
                months=args.months,
                currency=args.currency.upper(),
            )
            account_rows.append(rows)
            title = account_title(account)
            render_cashflow_details(
                events,
                console,
                start_date=start_date,
                months=args.months,
                title=f"Future portfolio cashflow details - {title}",
            )
            render_cashflow(rows, console, title=f"Monthly portfolio cashflow forecast - {title}")
            render_maturity_details(events, console, title=f"Maturity details - {title}")
        if len(account_rows) > 1:
            render_cashflow(
                combine_monthly_cashflows(account_rows, currency=args.currency.upper()),
                console,
                title="Monthly portfolio cashflow forecast - All accounts total",
            )
    return 0


def floating_forecast_command(args: argparse.Namespace, console: Console) -> int:
    if args.months < 1:
        console.print("[red]--months must be at least 1[/red]")
        return 2

    try:
        settings = load_settings()
        formulas = load_floating_coupon_formulas(args.formulas)
        scenario = load_rate_scenario(args.scenarios, args.scenario)
    except (ConfigError, OSError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    configure_t_invest_sdk()
    from t_tech.invest import Client

    start_date = args.as_of
    to_date = _add_months(date(start_date.year, start_date.month, 1), args.months)
    with Client(settings.invest_token) as client:
        accounts = [
            AccountSummary(
                id=account.id,
                name=getattr(account, "name", ""),
                type=str(getattr(account, "type", "")),
                status=str(getattr(account, "status", "")),
                access_level=str(getattr(account, "access_level", "")),
            )
            for account in client.users.get_accounts().accounts
        ]
        selected_accounts = select_accounts(args.account_id, accounts, console)
        if not selected_accounts:
            return 2

        service = TInvestFloatingBondService(client)
        for account in selected_accounts:
            positions = service.get_floating_bond_positions(account.id, start_date, to_date)
            events = build_floating_coupon_forecast(
                bond_positions=positions,
                formulas_by_isin=formulas,
                scenario=scenario,
                start_date=start_date,
                months=args.months,
            )
            if not events:
                continue
            rows = aggregate_monthly_floating_forecast(events, start_date=start_date, months=args.months)
            title = account_title(account)
            render_floating_details(
                events,
                console,
                title=f"Floating coupon forecast: scenario={scenario.name} - {title}",
                only_unknown=args.only_unknown,
            )
            render_monthly_floating_forecast(rows, console, title=f"Floating coupon monthly summary - {title}")
            render_floating_summary(rows, console, months=args.months)
    return 0


def floating_scenarios_command(args: argparse.Namespace, console: Console) -> int:
    if args.months < 1:
        console.print("[red]--months must be at least 1[/red]")
        return 2
    if args.delta_percent < Decimal("0"):
        console.print("[red]--delta-percent must be non-negative[/red]")
        return 2

    try:
        settings = load_settings()
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    configure_t_invest_sdk()
    from t_tech.invest import Client

    start_date = args.as_of
    to_date = _add_months(date(start_date.year, start_date.month, 1), args.months)
    with Client(settings.invest_token) as client:
        accounts = [
            AccountSummary(
                id=account.id,
                name=getattr(account, "name", ""),
                type=str(getattr(account, "type", "")),
                status=str(getattr(account, "status", "")),
                access_level=str(getattr(account, "access_level", "")),
            )
            for account in client.users.get_accounts().accounts
        ]
        selected_accounts = select_accounts(args.account_id, accounts, console)
        if not selected_accounts:
            return 2

        service = TInvestFloatingScenarioService(client)
        for account in selected_accounts:
            positions = service.get_floating_scenario_positions(account.id, start_date, to_date)
            if not positions:
                continue
            events = build_floating_scenario_forecast(
                positions=positions,
                months=args.months,
                delta_percent=args.delta_percent,
                start_date=start_date,
            )
            if not events:
                continue
            title = account_title(account)
            if args.details:
                render_floating_scenario_details(events, console, title=f"Floating coupon scenarios - {title}")
            monthly = aggregate_monthly_scenarios(events)
            render_monthly_scenario_forecast(monthly, console, title=f"Floating coupon scenario monthly summary - {title}")
            render_scenario_portfolio_summary(events, console, months=args.months)
    return 0


def offers_command(args: argparse.Namespace, console: Console) -> int:
    if args.days < 1:
        console.print("[red]--days must be at least 1[/red]")
        return 2
    if args.warning_days < 0:
        console.print("[red]--warning-days must be non-negative[/red]")
        return 2

    try:
        settings = load_settings()
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    configure_t_invest_sdk()
    from t_tech.invest import Client

    from_date = args.as_of
    to_date = date.fromordinal(from_date.toordinal() + args.days)
    with Client(settings.invest_token) as client:
        accounts = [
            AccountSummary(
                id=account.id,
                name=getattr(account, "name", ""),
                type=str(getattr(account, "type", "")),
                status=str(getattr(account, "status", "")),
                access_level=str(getattr(account, "access_level", "")),
            )
            for account in client.users.get_accounts().accounts
        ]
        selected_accounts = select_accounts(args.account_id, accounts, console)
        if not selected_accounts:
            return 2

        service = TInvestBondOfferService(client)
        for account in selected_accounts:
            offers = service.get_upcoming_offers(
                account_id=account.id,
                from_date=from_date,
                to_date=to_date,
                warning_days=args.warning_days,
            )
            if not offers:
                continue
            title = account_title(account)
            render_offers(offers, console, title=f"Upcoming bond offers - {title}")
            render_offer_summary(offers, console)
            render_offer_warnings(offers, console)
    return 0


def portfolio_all_command(args: argparse.Namespace, console: Console) -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    configure_t_invest_sdk()
    from t_tech.invest import Client

    with Client(settings.invest_token) as client:
        accounts = [
            AccountSummary(
                id=account.id,
                name=getattr(account, "name", ""),
                type=str(getattr(account, "type", "")),
                status=str(getattr(account, "status", "")),
                access_level=str(getattr(account, "access_level", "")),
            )
            for account in client.users.get_accounts().accounts
        ]
        selected_accounts = select_accounts(args.account_id, accounts, console)
        if not selected_accounts:
            return 2

        service = TInvestPortfolioAllService(client)
        repository = PortfolioAllRepository(args.db_path)
        snapshots: list[PortfolioSnapshot] = []
        for account in selected_accounts:
            snapshot = service.get_portfolio_snapshot(account.id, args.as_of)
            if not snapshot.assets:
                continue
            snapshot_id = repository.save_snapshot(snapshot)
            snapshots.append(snapshot)
            title = account_title(account)
            render_portfolio_assets(snapshot.assets, console, title=f"Full portfolio - {title}")
            console.print(f"Saved full portfolio snapshot #{snapshot_id} for {title} as of {format_date(args.as_of)} to {args.db_path}")

        if len(snapshots) > 1:
            render_portfolio_assets(
                combine_portfolio_assets(snapshots),
                console,
                title="Full portfolio - All accounts total",
            )
    return 0


def render_cashflow(
    rows: list[MonthlyCashflow],
    console: Console,
    *,
    title: str = "Monthly portfolio cashflow forecast",
) -> None:
    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Month", overflow="fold")
    table.add_column("Fixed coupons", justify="right", overflow="fold")
    table.add_column("Floaters", justify="right", overflow="fold")
    table.add_column("Dividends", justify="right", overflow="fold")
    table.add_column("Amortization", justify="right", overflow="fold")
    table.add_column("Maturity", justify="right", overflow="fold")
    table.add_column("Total", justify="right", overflow="fold")

    for row in rows:
        table.add_row(
            row.month,
            format_money(row.fixed_coupons, row.currency),
            format_money(row.floating_coupons, row.currency),
            format_money(row.dividends, row.currency),
            format_money(row.amortizations, row.currency),
            format_money(row.maturities, row.currency),
            format_money(row.total, row.currency),
        )
    console.print(table)


def render_portfolio_assets(
    assets: list[PortfolioAsset],
    console: Console,
    *,
    title: str = "Full portfolio",
) -> None:
    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Name", overflow="fold")
    table.add_column("ISIN", overflow="fold")
    table.add_column("Qty", justify="right", overflow="fold")
    table.add_column("Avg Buy", justify="right", overflow="fold")
    table.add_column("Current", justify="right", overflow="fold")
    for asset in sorted(assets, key=lambda item: (item.name, item.isin)):
        table.add_row(
            asset.name,
            asset.isin,
            format_decimal(asset.quantity),
            format_optional_money(asset.average_position_price, asset.price_currency or ""),
            format_optional_money(asset.current_price, asset.price_currency or ""),
        )
    console.print(table)


def combine_portfolio_assets(snapshots: list[PortfolioSnapshot]) -> list[PortfolioAsset]:
    grouped: dict[tuple[str, str], PortfolioAsset] = {}
    for snapshot in snapshots:
        for asset in snapshot.assets:
            key = (asset.name, asset.isin)
            if key not in grouped:
                grouped[key] = asset.model_copy(update={"account_id": "ALL"})
                continue
            existing = grouped[key]
            grouped[key] = existing.model_copy(update={"quantity": existing.quantity + asset.quantity})
    return list(grouped.values())


def render_offers(
    offers: list[BondOfferEvent],
    console: Console,
    *,
    title: str = "Upcoming bond offers",
) -> None:
    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Bond", overflow="fold")
    table.add_column("Offer date", overflow="fold")
    table.add_column("Days left", justify="right", overflow="fold")
    table.add_column("Type", overflow="fold")
    table.add_column("Quantity", justify="right", overflow="fold")
    table.add_column("Status", overflow="fold")
    for offer in offers:
        table.add_row(
            offer.name,
            format_date(offer.offer_date),
            str(offer.days_until_offer),
            offer.event_type.name,
            format_decimal(offer.quantity),
            offer.status.name,
        )
    console.print(table)


def render_offer_summary(offers: list[BondOfferEvent], console: Console) -> None:
    counts = offer_summary_counts(offers)
    console.print("Offer summary")
    console.print(f"Offers within 30 days:\n    {counts[30]} bonds")
    console.print(f"Offers within 45 days:\n    {counts[45]} bonds")
    console.print(f"Offers within 90 days:\n    {counts[90]} bonds")


def render_offer_warnings(offers: list[BondOfferEvent], console: Console) -> None:
    warnings = [offer for offer in offers if offer.status == OfferStatus.WARNING]
    if not warnings:
        return
    console.print("Action required soon")
    for offer in warnings:
        console.print(f"- {offer.name} -> offer in {offer.days_until_offer} days")


def render_floating_scenario_details(
    events: list[FloatingScenarioCouponEvent],
    console: Console,
    *,
    title: str = "Floating coupon scenarios",
) -> None:
    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Bond", overflow="fold")
    table.add_column("Date", overflow="fold")
    table.add_column("Scenario", overflow="fold")
    table.add_column("Source", overflow="fold")
    table.add_column("Base coupon", justify="right", overflow="fold")
    table.add_column("Rate", justify="right", overflow="fold")
    table.add_column("Forecast coupon", justify="right", overflow="fold")
    table.add_column("Qty", justify="right", overflow="fold")
    table.add_column("Total", justify="right", overflow="fold")
    for event in events:
        table.add_row(
            event.name,
            format_date(event.coupon_date),
            event.scenario.name,
            event.source.value,
            format_money(event.base_coupon_per_bond, event.currency),
            format_percent(event.annual_coupon_rate_percent),
            format_money(event.coupon_per_bond, event.currency),
            format_decimal(event.quantity),
            format_money(event.total_coupon, event.currency),
        )
    console.print(table)


def render_monthly_scenario_forecast(
    rows: list[MonthlyScenarioForecast],
    console: Console,
    *,
    title: str = "Floating coupon scenario monthly summary",
) -> None:
    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Month", overflow="fold")
    table.add_column("Scenario", overflow="fold")
    table.add_column("Total coupons", justify="right", overflow="fold")
    for row in rows:
        table.add_row(row.month, row.scenario.name, format_money(row.total_coupons, row.currency))
    console.print(table)


def render_scenario_portfolio_summary(events: list[FloatingScenarioCouponEvent], console: Console, *, months: int) -> None:
    totals = {scenario: Decimal("0") for scenario in ScenarioType}
    currency = events[0].currency if events else "RUB"
    for event in events:
        totals[event.scenario] += event.total_coupon
    console.print(f"{months}-month forecast based on last known coupon")
    for scenario in ScenarioType:
        console.print(f"{scenario.name}:")
        console.print(f"    {format_money(totals[scenario], currency)}")


def render_floating_details(
    events: list[FloatingCouponForecastEvent],
    console: Console,
    *,
    title: str = "Floating coupon forecast",
    only_unknown: bool = False,
) -> None:
    shown_events = [event for event in events if not only_unknown or event.source == CouponForecastSource.UNKNOWN]
    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Bond", overflow="fold")
    table.add_column("Date", overflow="fold")
    table.add_column("Source", overflow="fold")
    table.add_column("Index", overflow="fold")
    table.add_column("Index rate", justify="right", overflow="fold")
    table.add_column("Spread", justify="right", overflow="fold")
    table.add_column("Coupon/bond", justify="right", overflow="fold")
    table.add_column("Qty", justify="right", overflow="fold")
    table.add_column("Total", justify="right", overflow="fold")

    for event in shown_events:
        table.add_row(
            event.name,
            format_date(event.coupon_date),
            event.source.value,
            event.index.name,
            format_percent(event.index_rate_percent),
            format_bps_as_percent(event.spread_bps),
            format_optional_money(event.coupon_per_bond, event.currency),
            format_decimal(event.quantity),
            format_optional_money(event.total_coupon, event.currency),
        )
    console.print(table)


def render_monthly_floating_forecast(
    rows: list[MonthlyFloatingCouponForecast],
    console: Console,
    *,
    title: str = "Floating coupon monthly summary",
) -> None:
    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Month", overflow="fold")
    table.add_column("Actual coupons", justify="right", overflow="fold")
    table.add_column("Forecast coupons", justify="right", overflow="fold")
    table.add_column("Unknown events", justify="right", overflow="fold")
    table.add_column("Total", justify="right", overflow="fold")
    for row in rows:
        table.add_row(
            row.month,
            format_money(row.actual_coupons, row.currency),
            format_money(row.forecast_coupons, row.currency),
            str(row.unknown_count),
            format_money(row.total_known_and_forecast, row.currency),
        )
    console.print(table)


def render_floating_summary(rows: list[MonthlyFloatingCouponForecast], console: Console, *, months: int) -> None:
    actual = sum((row.actual_coupons for row in rows), Decimal("0"))
    forecast = sum((row.forecast_coupons for row in rows), Decimal("0"))
    unknown = sum(row.unknown_count for row in rows)
    currency = rows[0].currency if rows else "RUB"
    console.print(f"{months}-month forecast:")
    console.print(f"- actual announced coupons: {format_money(actual, currency)}")
    console.print(f"- forecast coupons: {format_money(forecast, currency)}")
    console.print(f"- unknown events: {unknown}")
    console.print(f"- total known + forecast: {format_money(actual + forecast, currency)}")


def render_maturity_details(
    events: list[CashflowEvent],
    console: Console,
    *,
    title: str = "Maturity details",
) -> None:
    maturities = sorted(
        (event for event in events if event.event_type == CashflowType.MATURITY),
        key=lambda event: (event.event_date, event.name, event.isin or ""),
    )
    if not maturities:
        return

    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Date", overflow="fold")
    table.add_column("Month", overflow="fold")
    table.add_column("Name", overflow="fold")
    table.add_column("ISIN", overflow="fold")
    table.add_column("Qty", justify="right", overflow="fold")
    table.add_column("Per Bond", justify="right", overflow="fold")
    table.add_column("Total", justify="right", overflow="fold")

    for event in maturities:
        table.add_row(
            format_date(event.event_date),
            f"{event.event_date.year:04d}-{event.event_date.month:02d}",
            event.name,
            event.isin or "",
            format_decimal(event.quantity),
            format_money(event.amount_per_bond, event.currency),
            format_money(event.total_amount, event.currency),
        )
    console.print(table)


def render_cashflow_details(
    events: list[CashflowEvent],
    console: Console,
    *,
    start_date: date,
    months: int,
    title: str = "Future portfolio cashflow details",
) -> None:
    window_end = _add_months(date(start_date.year, start_date.month, 1), months)
    future_events = sorted(
        (event for event in events if start_date <= event.event_date < window_end),
        key=lambda event: (event.event_date, event.event_type, event.name, event.isin or ""),
    )
    if not future_events:
        return

    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Date", overflow="fold")
    table.add_column("Month", overflow="fold")
    table.add_column("Type", overflow="fold")
    table.add_column("Name", overflow="fold")
    table.add_column("ISIN", overflow="fold")
    table.add_column("Qty", justify="right", overflow="fold")
    table.add_column("Payment/unit", justify="right", overflow="fold")
    table.add_column("Total", justify="right", overflow="fold")
    table.add_column("Source", overflow="fold")

    for event in future_events:
        table.add_row(
            format_date(event.event_date),
            f"{event.event_date.year:04d}-{event.event_date.month:02d}",
            event.event_type.value,
            event.name,
            event.isin or "",
            format_decimal(event.quantity),
            format_payment_amount(event),
            format_money(event.total_amount, event.currency),
            format_cashflow_source(event.source),
        )
    console.print(table)


def combine_monthly_cashflows(
    account_rows: list[list[MonthlyCashflow]],
    *,
    currency: str = "RUB",
) -> list[MonthlyCashflow]:
    if not account_rows:
        return []

    month_order = [row.month for row in account_rows[0]]
    totals = {
        month: {
            "coupons": Decimal("0"),
            "fixed_coupons": Decimal("0"),
            "floating_coupons": Decimal("0"),
            "dividends": Decimal("0"),
            "amortizations": Decimal("0"),
            "maturities": Decimal("0"),
        }
        for month in month_order
    }
    for rows in account_rows:
        for row in rows:
            if row.month not in totals:
                totals[row.month] = {
                    "coupons": Decimal("0"),
                    "fixed_coupons": Decimal("0"),
                    "floating_coupons": Decimal("0"),
                    "dividends": Decimal("0"),
                    "amortizations": Decimal("0"),
                    "maturities": Decimal("0"),
                }
                month_order.append(row.month)
            totals[row.month]["coupons"] += row.coupons
            totals[row.month]["fixed_coupons"] += row.fixed_coupons
            totals[row.month]["floating_coupons"] += row.floating_coupons
            totals[row.month]["dividends"] += row.dividends
            totals[row.month]["amortizations"] += row.amortizations
            totals[row.month]["maturities"] += row.maturities

    return [
        MonthlyCashflow(
            month=month,
            coupons=totals[month]["coupons"],
            fixed_coupons=totals[month]["fixed_coupons"],
            floating_coupons=totals[month]["floating_coupons"],
            dividends=totals[month]["dividends"],
            amortizations=totals[month]["amortizations"],
            maturities=totals[month]["maturities"],
            total=totals[month]["coupons"] + totals[month]["dividends"] + totals[month]["amortizations"] + totals[month]["maturities"],
            currency=currency,
        )
        for month in sorted(month_order)
    ]


def format_money(value: Decimal, currency: str) -> str:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    formatted = f"{rounded:,.2f}".replace(",", " ")
    suffix = "₽" if currency.upper() == "RUB" else currency.upper()
    return f"{formatted} {suffix}"


def format_optional_money(value: Decimal | None, currency: str) -> str:
    if value is None:
        return "-"
    return format_money(value, currency)


def format_payment_amount(event: CashflowEvent) -> str:
    amount = event.payment_amount_per_unit if event.payment_amount_per_unit is not None else event.amount_per_bond
    currency = event.payment_currency or event.currency
    return format_money(amount, currency)


def format_percent(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}%"


def format_bps_as_percent(value: int | None) -> str:
    if value is None:
        return "-"
    percent = Decimal(value) / Decimal("100")
    return f"{percent.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}%"


def format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def format_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def format_cashflow_source(value: CashflowSource) -> str:
    if value == CashflowSource.FLOATING_COUPON:
        return "floating"
    if value == CashflowSource.REPEATED_FLOATING_COUPON:
        return "floating: last coupon"
    return value.value


def parse_cli_date(value: str) -> date:
    try:
        day, month, year = value.split(".")
        return date(int(year), int(month), int(day))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use DD.MM.YYYY format") from exc


if __name__ == "__main__":
    raise SystemExit(main())
