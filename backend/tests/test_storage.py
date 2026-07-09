from datetime import date, datetime, timezone
from decimal import Decimal

from invest_bonds.models import (
    BondAnalysis,
    BondCoupon,
    BondEvent,
    BondEventType,
    BondHolding,
    BondInstrument,
    BondPosition,
    BondSnapshot,
    Signal,
)
from invest_bonds.storage import SnapshotRepository


def test_save_snapshot_smoke(tmp_path) -> None:
    snapshot = BondSnapshot(
        account_id="account-1",
        fetched_at=datetime(2026, 4, 27, tzinfo=timezone.utc),
        as_of=date(2026, 4, 27),
        holdings=[
            BondHolding(
                instrument=BondInstrument(
                    uid="uid-1",
                    figi="figi-1",
                    isin="RU0000000001",
                    name="Test Bond",
                    nominal=Decimal("1000"),
                    nominal_currency="rub",
                    maturity_date=date(2027, 1, 1),
                ),
                position=BondPosition(
                    instrument_uid="uid-1",
                    figi="figi-1",
                    quantity=Decimal("2"),
                    quantity_lots=Decimal("2"),
                ),
                coupons=[BondCoupon(instrument_uid="uid-1", figi="figi-1", coupon_date=date(2026, 6, 1))],
                events=[BondEvent(instrument_uid="uid-1", event_type=BondEventType.MATURITY, event_date=date(2027, 1, 1))],
                analysis=BondAnalysis(signal=Signal.HOLD, nearest_event_date=date(2026, 6, 1), nearest_event_type="COUPON"),
            )
        ],
    )
    repo = SnapshotRepository(tmp_path / "invest.db")

    snapshot_id = repo.save_snapshot(snapshot)

    assert snapshot_id == 1
    assert repo.count_rows("snapshots") == 1
    assert repo.count_rows("bond_instruments") == 1
    assert repo.count_rows("bond_positions") == 1
    assert repo.count_rows("bond_coupons") == 1
    assert repo.count_rows("bond_events") == 1
