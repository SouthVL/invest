from __future__ import annotations

import sqlite3
from datetime import timezone
from decimal import Decimal
from pathlib import Path

from app.domain.portfolio_all import PortfolioSnapshot


class PortfolioAllRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save_snapshot(self, snapshot: PortfolioSnapshot) -> int:
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            self._create_schema(conn)
            cursor = conn.execute(
                """
                INSERT INTO portfolio_snapshots(account_id, fetched_at, as_of)
                VALUES (?, ?, ?)
                """,
                (
                    snapshot.account_id,
                    snapshot.fetched_at.astimezone(timezone.utc).isoformat(),
                    snapshot.as_of.isoformat(),
                ),
            )
            snapshot_id = int(cursor.lastrowid)
            conn.executemany(
                """
                INSERT INTO portfolio_assets(
                    snapshot_id, account_id, instrument_uid, position_uid, figi, ticker,
                    instrument_type, name, isin, quantity, average_position_price,
                    current_price, price_currency
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        snapshot_id,
                        asset.account_id,
                        asset.instrument_uid,
                        asset.position_uid,
                        asset.figi,
                        asset.ticker,
                        asset.instrument_type,
                        asset.name,
                        asset.isin,
                        str(asset.quantity),
                        _decimal_text(asset.average_position_price),
                        _decimal_text(asset.current_price),
                        asset.price_currency,
                    )
                    for asset in snapshot.assets
                ],
            )
            return snapshot_id

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                as_of TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL REFERENCES portfolio_snapshots(id) ON DELETE CASCADE,
                account_id TEXT NOT NULL,
                instrument_uid TEXT,
                position_uid TEXT,
                figi TEXT,
                ticker TEXT,
                instrument_type TEXT,
                name TEXT,
                isin TEXT,
                quantity TEXT NOT NULL,
                average_position_price TEXT,
                current_price TEXT,
                price_currency TEXT
            );
            """
        )


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)
