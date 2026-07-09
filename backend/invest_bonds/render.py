from __future__ import annotations

from datetime import date
from decimal import Decimal

from rich import box
from rich.console import Console
from rich.table import Table

from invest_bonds.models import AccountSummary, BondHolding


def _date(value: date | None) -> str:
    return "" if value is None else value.strftime("%d.%m.%Y")


def _money(value: Decimal | None, currency: str | None = None) -> str:
    if value is None:
        return ""
    suffix = f" {currency.upper()}" if currency else ""
    return f"{_decimal(value)}{suffix}"


def _decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def render_accounts(accounts: list[AccountSummary], console: Console) -> None:
    table = Table(title="T-Invest Accounts", box=box.SQUARE, show_lines=True)
    table.add_column("Account ID")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Access")
    for account in accounts:
        table.add_row(account.id, account.name, account.type, account.status, account.access_level)
    console.print(table)


def render_bonds(holdings: list[BondHolding], console: Console, *, title: str = "Bond Portfolio") -> None:
    table = Table(title=title, box=box.SQUARE, show_lines=True)
    table.add_column("Name", overflow="fold")
    table.add_column("ISIN", overflow="fold")
    table.add_column("Qty", justify="right", overflow="fold")
    table.add_column("Nominal", justify="right", overflow="fold")
    table.add_column("Avg Buy", justify="right", overflow="fold")
    table.add_column("Current", justify="right", overflow="fold")
    table.add_column("Maturity", overflow="fold")
    table.add_column("Next Coupon", overflow="fold")
    table.add_column("Offer/Call", overflow="fold")
    table.add_column("Nearest", overflow="fold")
    table.add_column("Signal", overflow="fold")

    for holding in sorted(holdings, key=_sort_key):
        instrument = holding.instrument
        position = holding.position
        analysis = holding.analysis
        table.add_row(
            instrument.name or position.ticker or instrument.figi,
            instrument.isin,
            _decimal(position.quantity),
            _money(instrument.nominal, instrument.nominal_currency),
            _money(position.average_position_price, position.price_currency),
            _money(position.current_price, position.price_currency),
            _date(instrument.maturity_date),
            _date(analysis.next_coupon_date),
            _date(analysis.next_offer_date),
            f"{analysis.nearest_event_type} {_date(analysis.nearest_event_date)}".strip(),
            analysis.signal,
        )
    console.print(table)


def _sort_key(holding: BondHolding) -> tuple[date, str]:
    return (holding.analysis.nearest_event_date or date.max, holding.instrument.name)
