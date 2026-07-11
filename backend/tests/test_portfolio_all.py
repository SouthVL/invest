from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3
from types import SimpleNamespace

from rich.console import Console

from app.t_invest.portfolio_all import TInvestPortfolioAllService, normalize_instrument_type
from app.cli import combine_portfolio_assets, render_portfolio_assets
from app.domain.portfolio_all import PortfolioAsset, PortfolioSnapshot
from app.storage.portfolio_all import PortfolioAllRepository


def asset(name: str = "Bond A", isin: str = "RU000A", qty: str = "10") -> PortfolioAsset:
    return PortfolioAsset(
        account_id="account-1",
        instrument_uid=f"uid-{isin}",
        name=name,
        isin=isin,
        quantity=Decimal(qty),
        average_position_price=Decimal("99.50"),
        current_price=Decimal("101.25"),
        price_currency="rub",
    )


def test_save_full_portfolio_snapshot(tmp_path) -> None:
    snapshot = PortfolioSnapshot(
        account_id="account-1",
        fetched_at=datetime(2026, 5, 14, tzinfo=timezone.utc),
        as_of=date(2026, 5, 14),
        assets=[asset()],
    )
    db_path = tmp_path / "invest.db"

    snapshot_id = PortfolioAllRepository(db_path).save_snapshot(snapshot)

    with sqlite3.connect(db_path) as conn:
        assert snapshot_id == 1
        assert conn.execute("SELECT COUNT(*) FROM portfolio_snapshots").fetchone()[0] == 1
        assert conn.execute("SELECT name, isin, quantity, average_position_price, current_price FROM portfolio_assets").fetchone() == (
            "Bond A",
            "RU000A",
            "10",
            "99.50",
            "101.25",
        )


def test_render_full_portfolio_table() -> None:
    console = Console(record=True, width=140)

    render_portfolio_assets([asset()], console)

    rendered = console.export_text()
    assert "Full portfolio" in rendered
    assert "Name" in rendered
    assert "ISIN" in rendered
    assert "Qty" in rendered
    assert "Avg Buy" in rendered
    assert "Current" in rendered
    assert "Bond A" in rendered


def test_combine_portfolio_assets_sums_quantity_by_name_and_isin() -> None:
    snapshots = [
        PortfolioSnapshot(account_id="a1", fetched_at=datetime.now(timezone.utc), as_of=date(2026, 5, 14), assets=[asset(qty="10")]),
        PortfolioSnapshot(account_id="a2", fetched_at=datetime.now(timezone.utc), as_of=date(2026, 5, 14), assets=[asset(qty="5")]),
    ]

    combined = combine_portfolio_assets(snapshots)

    assert len(combined) == 1
    assert combined[0].quantity == Decimal("15")


def test_tinvest_portfolio_asset_normalizes_instrument_kind() -> None:
    from t_tech.invest.schemas import InstrumentType

    service = TInvestPortfolioAllService(client=SimpleNamespace())
    position = SimpleNamespace(
        figi="SHAREFIGI",
        instrument_uid="share-uid",
        position_uid="",
        ticker="SHARE",
        instrument_type="bond",
        quantity=SimpleNamespace(units=3, nano=0),
        average_position_price=SimpleNamespace(units=10, nano=0, currency="RUB"),
        current_price=SimpleNamespace(units=12, nano=0, currency="RUB"),
    )
    instrument = SimpleNamespace(
        uid="share-uid",
        position_uid="position-share",
        figi="SHAREFIGI",
        ticker="SHARE",
        instrument_kind=InstrumentType.INSTRUMENT_TYPE_SHARE,
        instrument_type="share",
        name="Share",
        isin="RU000SHARE",
    )
    service._instrument = lambda _: instrument  # type: ignore[assignment]

    asset = service._asset_from_position("account-1", position)

    assert asset.instrument_type == "share"


def test_normalize_instrument_type_accepts_tinvest_aliases() -> None:
    from t_tech.invest.schemas import InstrumentType

    assert normalize_instrument_type(InstrumentType.INSTRUMENT_TYPE_BOND) == "bond"
    assert normalize_instrument_type("INSTRUMENT_TYPE_SHARE") == "share"
    assert normalize_instrument_type("Stock") == "share"
    assert normalize_instrument_type("INSTRUMENT_TYPE_UNSPECIFIED", "bond") == "bond"
