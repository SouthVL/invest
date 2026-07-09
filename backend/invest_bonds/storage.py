from __future__ import annotations

import sqlite3
from datetime import timezone
from decimal import Decimal
from pathlib import Path

from invest_bonds.models import BondSnapshot


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _date_text(value) -> str | None:
    return None if value is None else value.isoformat()


def _bool_int(value: bool) -> int:
    return 1 if value else 0


class SnapshotRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save_snapshot(self, snapshot: BondSnapshot) -> int:
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            self._create_schema(conn)
            cursor = conn.execute(
                """
                INSERT INTO snapshots(account_id, fetched_at, as_of)
                VALUES (?, ?, ?)
                """,
                (
                    snapshot.account_id,
                    snapshot.fetched_at.astimezone(timezone.utc).isoformat(),
                    snapshot.as_of.isoformat(),
                ),
            )
            snapshot_id = int(cursor.lastrowid)
            for holding in snapshot.holdings:
                self._save_holding(conn, snapshot_id, holding)
            return snapshot_id

    def count_rows(self, table: str) -> int:
        allowed = {"snapshots", "bond_positions", "bond_instruments", "bond_coupons", "bond_events"}
        if table not in allowed:
            raise ValueError(f"Unsupported table: {table}")
        with sqlite3.connect(self.path) as conn:
            self._create_schema(conn)
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                as_of TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bond_instruments (
                uid TEXT PRIMARY KEY,
                position_uid TEXT,
                figi TEXT,
                isin TEXT,
                name TEXT,
                nominal_amount TEXT,
                nominal_currency TEXT,
                maturity_date TEXT,
                coupon_quantity_per_year INTEGER,
                floating_coupon_flag INTEGER NOT NULL,
                perpetual_flag INTEGER NOT NULL,
                amortization_flag INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bond_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
                instrument_uid TEXT NOT NULL REFERENCES bond_instruments(uid),
                position_uid TEXT,
                figi TEXT,
                ticker TEXT,
                quantity TEXT NOT NULL,
                quantity_lots TEXT NOT NULL,
                average_position_price TEXT,
                current_price TEXT,
                price_currency TEXT,
                expected_yield TEXT
            );

            CREATE TABLE IF NOT EXISTS bond_coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
                instrument_uid TEXT NOT NULL REFERENCES bond_instruments(uid),
                figi TEXT,
                coupon_date TEXT NOT NULL,
                pay_one_bond TEXT,
                currency TEXT,
                coupon_type TEXT,
                coupon_period INTEGER
            );

            CREATE TABLE IF NOT EXISTS bond_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
                instrument_uid TEXT NOT NULL REFERENCES bond_instruments(uid),
                event_type TEXT NOT NULL,
                event_date TEXT,
                pay_date TEXT,
                amount TEXT,
                currency TEXT,
                value TEXT,
                note TEXT
            );
            """
        )

    def _save_holding(self, conn: sqlite3.Connection, snapshot_id: int, holding) -> None:
        instrument = holding.instrument
        position = holding.position
        conn.execute(
            """
            INSERT INTO bond_instruments(
                uid, position_uid, figi, isin, name, nominal_amount, nominal_currency,
                maturity_date, coupon_quantity_per_year, floating_coupon_flag,
                perpetual_flag, amortization_flag
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET
                position_uid=excluded.position_uid,
                figi=excluded.figi,
                isin=excluded.isin,
                name=excluded.name,
                nominal_amount=excluded.nominal_amount,
                nominal_currency=excluded.nominal_currency,
                maturity_date=excluded.maturity_date,
                coupon_quantity_per_year=excluded.coupon_quantity_per_year,
                floating_coupon_flag=excluded.floating_coupon_flag,
                perpetual_flag=excluded.perpetual_flag,
                amortization_flag=excluded.amortization_flag
            """,
            (
                instrument.uid,
                instrument.position_uid,
                instrument.figi,
                instrument.isin,
                instrument.name,
                _decimal_text(instrument.nominal),
                instrument.nominal_currency,
                _date_text(instrument.maturity_date),
                instrument.coupon_quantity_per_year,
                _bool_int(instrument.floating_coupon_flag),
                _bool_int(instrument.perpetual_flag),
                _bool_int(instrument.amortization_flag),
            ),
        )
        conn.execute(
            """
            INSERT INTO bond_positions(
                snapshot_id, instrument_uid, position_uid, figi, ticker, quantity,
                quantity_lots, average_position_price, current_price, price_currency,
                expected_yield
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                position.instrument_uid,
                position.position_uid,
                position.figi,
                position.ticker,
                str(position.quantity),
                str(position.quantity_lots),
                _decimal_text(position.average_position_price),
                _decimal_text(position.current_price),
                position.price_currency,
                _decimal_text(position.expected_yield),
            ),
        )
        conn.executemany(
            """
            INSERT INTO bond_coupons(
                snapshot_id, instrument_uid, figi, coupon_date, pay_one_bond,
                currency, coupon_type, coupon_period
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_id,
                    coupon.instrument_uid,
                    coupon.figi,
                    coupon.coupon_date.isoformat(),
                    _decimal_text(coupon.pay_one_bond),
                    coupon.currency,
                    coupon.coupon_type,
                    coupon.coupon_period,
                )
                for coupon in holding.coupons
            ],
        )
        conn.executemany(
            """
            INSERT INTO bond_events(
                snapshot_id, instrument_uid, event_type, event_date, pay_date,
                amount, currency, value, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_id,
                    event.instrument_uid,
                    event.event_type,
                    _date_text(event.event_date),
                    _date_text(event.pay_date),
                    _decimal_text(event.amount),
                    event.currency,
                    _decimal_text(event.value),
                    event.note,
                )
                for event in holding.events
            ],
        )
