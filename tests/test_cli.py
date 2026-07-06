from datetime import date, datetime, timezone
from decimal import Decimal

from rich.console import Console

from invest_bonds.cli import main
from invest_bonds.models import AccountSummary, BondAnalysis, BondHolding, BondInstrument, BondPosition, BondSnapshot, Signal


class FakeAdapter:
    def __init__(self) -> None:
        self.fetch_calls = []

    def get_accounts(self) -> list[AccountSummary]:
        return [AccountSummary(id="account-1", name="Broker")]

    def fetch_snapshot(self, *, account_id: str, as_of: date, lookahead_days: int) -> BondSnapshot:
        self.fetch_calls.append((account_id, as_of, lookahead_days))
        return BondSnapshot(
            account_id=account_id,
            fetched_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
            as_of=as_of,
            holdings=[
                BondHolding(
                    instrument=BondInstrument(uid="uid-1", name="Test Bond", isin="RU0000000001"),
                    position=BondPosition(instrument_uid="uid-1", quantity=Decimal("1"), quantity_lots=Decimal("1")),
                    analysis=BondAnalysis(signal=Signal.HOLD),
                )
            ],
        )


class EmptyAdapter:
    def get_accounts(self) -> list[AccountSummary]:
        return [AccountSummary(id="empty-account", name="Empty")]

    def fetch_snapshot(self, *, account_id: str, as_of: date, lookahead_days: int) -> BondSnapshot:
        return BondSnapshot(
            account_id=account_id,
            fetched_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
            as_of=as_of,
            holdings=[],
        )


def test_cli_uses_single_account_and_saves_snapshot(tmp_path) -> None:
    adapter = FakeAdapter()
    console = Console(record=True, width=120)
    code = main(
        ["--db-path", str(tmp_path / "invest.db"), "--as-of", "27.04.2026", "--lookahead-days", "10"],
        adapter=adapter,
        console=console,
    )

    assert code == 0
    assert adapter.fetch_calls == [("account-1", date(2026, 4, 27), 10)]
    assert "Bond Portfolio" in console.export_text()


def test_cli_fetches_all_accounts_without_account_id(tmp_path) -> None:
    class MultipleAccounts(FakeAdapter):
        def get_accounts(self) -> list[AccountSummary]:
            return [AccountSummary(id="a1", name="First"), AccountSummary(id="a2", name="Second")]

    adapter = MultipleAccounts()
    console = Console(record=True, width=120)
    code = main(["--db-path", str(tmp_path / "invest.db"), "--as-of", "27.04.2026"], adapter=adapter, console=console)

    assert code == 0
    assert adapter.fetch_calls == [("a1", date(2026, 4, 27), 730), ("a2", date(2026, 4, 27), 730)]
    rendered = console.export_text()
    assert "Bond Portfolio - First (a1)" in rendered
    assert "Bond Portfolio - Second (a2)" in rendered


def test_cli_does_not_render_bond_table_for_empty_account(tmp_path) -> None:
    console = Console(record=True, width=120)
    code = main(
        ["--db-path", str(tmp_path / "invest.db"), "--as-of", "27.04.2026"],
        adapter=EmptyAdapter(),
        console=console,
    )

    rendered = console.export_text()
    assert code == 0
    assert "No bonds found for Empty (empty-account)." in rendered
    assert "Bond Portfolio - Empty (empty-account)" not in rendered
