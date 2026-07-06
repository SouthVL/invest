from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Protocol

from rich.console import Console

from invest_bonds.adapter import TInvestAdapter
from invest_bonds.config import ConfigError, load_settings
from invest_bonds.models import AccountSummary, BondSnapshot
from invest_bonds.render import render_bonds
from invest_bonds.storage import SnapshotRepository


class PortfolioAdapter(Protocol):
    def get_accounts(self) -> list[AccountSummary]: ...

    def fetch_snapshot(self, *, account_id: str, as_of: date, lookahead_days: int) -> BondSnapshot: ...


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track a read-only T-Invest bond portfolio.")
    parser.add_argument("--account-id", help="T-Invest account id to fetch.")
    parser.add_argument("--db-path", default="invest.db", help="SQLite path. Defaults to invest.db.")
    parser.add_argument("--lookahead-days", type=int, default=730, help="Coupon/event lookahead window.")
    parser.add_argument("--as-of", type=parse_cli_date, default=date.today(), help="Analysis date as DD.MM.YYYY.")
    return parser


def main(argv: list[str] | None = None, *, adapter: PortfolioAdapter | None = None, console: Console | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    console = console or Console()

    if args.lookahead_days < 1:
        parser.error("--lookahead-days must be at least 1")

    try:
        if adapter is None:
            settings = load_settings()
            adapter = TInvestAdapter(settings.invest_token)

        accounts = adapter.get_accounts()
        selected_accounts = select_accounts(args.account_id, accounts, console)
        if not selected_accounts:
            return 2

        repository = SnapshotRepository(Path(args.db_path))
        for account in selected_accounts:
            snapshot = adapter.fetch_snapshot(account_id=account.id, as_of=args.as_of, lookahead_days=args.lookahead_days)
            snapshot_id = repository.save_snapshot(snapshot)
            title = account_title(account)
            if snapshot.holdings:
                render_bonds(snapshot.holdings, console, title=f"Bond Portfolio - {title}")
            else:
                console.print(f"No bonds found for {title}.")
            console.print(f"Saved snapshot #{snapshot_id} for {title} as of {format_date(args.as_of)} to {args.db_path}")
        return 0
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1


def select_accounts(account_id: str | None, accounts: list[AccountSummary], console: Console) -> list[AccountSummary]:
    if not accounts and not account_id:
        console.print("No T-Invest accounts found.")
        return []
    if account_id:
        matching = [account for account in accounts if account.id == account_id]
        if matching:
            return matching
        return [AccountSummary(id=account_id)]
    return accounts


def account_title(account: AccountSummary) -> str:
    if account.name:
        return f"{account.name} ({account.id})"
    return account.id


def parse_cli_date(value: str) -> date:
    try:
        day, month, year = value.split(".")
        return date(int(year), int(month), int(day))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must use DD.MM.YYYY format") from exc


def format_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")
