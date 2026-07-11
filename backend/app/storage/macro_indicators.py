from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.domain.macro_indicators import AnnualInflationValue, KeyRateValue, RuoniaValue


class MacroIndicatorsRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save_key_rate(self, value: KeyRateValue) -> int:
        return self._insert(
            indicator="key_rate",
            value_percent=value.value_percent,
            effective_date=value.effective_date,
            effective_from=value.effective_from,
            source=value.source,
            source_url=value.source_url,
            fetched_at=value.fetched_at,
            quality_status=value.quality_status,
        )

    def save_ruonia(self, value: RuoniaValue) -> int:
        return self._insert(
            indicator="ruonia",
            value_percent=value.value_percent,
            rate_date=value.rate_date,
            publication_date=value.publication_date,
            volume_rub_billion=value.volume_rub_billion,
            trades_count=value.trades_count,
            participants_count=value.participants_count,
            calculation_status=value.calculation_status,
            source=value.source,
            source_url=value.source_url,
            fetched_at=value.fetched_at,
            quality_status=value.quality_status,
        )

    def save_annual_inflation(self, value: AnnualInflationValue) -> int:
        return self._insert(
            indicator="annual_inflation",
            value_percent=value.value_percent_yoy,
            period_year=value.period_year,
            period_month=value.period_month,
            target_percent=value.target_percent,
            source=value.source,
            source_url=value.source_url,
            fetched_at=value.fetched_at,
            quality_status=value.quality_status,
        )

    def latest_key_rate(self) -> KeyRateValue | None:
        row = self._latest("key_rate")
        if row is None:
            return None
        return KeyRateValue(
            value_percent=_decimal(row["value_percent"]),
            effective_date=_date(row["effective_date"]),
            effective_from=_optional_date(row["effective_from"]),
            source=row["source"],
            source_url=row["source_url"],
            fetched_at=_datetime(row["fetched_at"]),
            quality_status=row["quality_status"],
        )

    def latest_ruonia(self) -> RuoniaValue | None:
        row = self._latest("ruonia")
        if row is None:
            return None
        return RuoniaValue(
            value_percent=_decimal(row["value_percent"]),
            rate_date=_date(row["rate_date"]),
            publication_date=_date(row["publication_date"]),
            volume_rub_billion=_optional_decimal(row["volume_rub_billion"]),
            trades_count=row["trades_count"],
            participants_count=row["participants_count"],
            calculation_status=row["calculation_status"],
            source=row["source"],
            source_url=row["source_url"],
            fetched_at=_datetime(row["fetched_at"]),
            quality_status=row["quality_status"],
        )

    def latest_annual_inflation(self) -> AnnualInflationValue | None:
        row = self._latest("annual_inflation")
        if row is None:
            return None
        return AnnualInflationValue(
            value_percent_yoy=_decimal(row["value_percent"]),
            period_year=row["period_year"],
            period_month=row["period_month"],
            target_percent=_optional_decimal(row["target_percent"]),
            source=row["source"],
            source_url=row["source_url"],
            fetched_at=_datetime(row["fetched_at"]),
            quality_status=row["quality_status"],
        )

    def count_rows(self) -> int:
        with self._connect() as conn:
            self._create_schema(conn)
            return int(conn.execute("SELECT COUNT(*) FROM macro_indicator_observations").fetchone()[0])

    def _insert(
        self,
        *,
        indicator: str,
        value_percent: Decimal,
        source: str,
        source_url: str,
        fetched_at: datetime,
        quality_status: str,
        effective_date: date | None = None,
        effective_from: date | None = None,
        rate_date: date | None = None,
        publication_date: date | None = None,
        volume_rub_billion: Decimal | None = None,
        trades_count: int | None = None,
        participants_count: int | None = None,
        calculation_status: str | None = None,
        period_year: int | None = None,
        period_month: int | None = None,
        target_percent: Decimal | None = None,
    ) -> int:
        with self._connect() as conn:
            self._create_schema(conn)
            cursor = conn.execute(
                """
                INSERT INTO macro_indicator_observations(
                    indicator, value_percent, effective_date, effective_from,
                    rate_date, publication_date, volume_rub_billion, trades_count,
                    participants_count, calculation_status, period_year, period_month,
                    target_percent, source, source_url, fetched_at, quality_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    indicator,
                    str(value_percent),
                    _date_text(effective_date),
                    _date_text(effective_from),
                    _date_text(rate_date),
                    _date_text(publication_date),
                    _decimal_text(volume_rub_billion),
                    trades_count,
                    participants_count,
                    calculation_status,
                    period_year,
                    period_month,
                    _decimal_text(target_percent),
                    source,
                    source_url,
                    _datetime_text(fetched_at),
                    quality_status,
                ),
            )
            return int(cursor.lastrowid)

    def _latest(self, indicator: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            self._create_schema(conn)
            return conn.execute(
                """
                SELECT *
                FROM macro_indicator_observations
                WHERE indicator = ?
                ORDER BY fetched_at DESC, id DESC
                LIMIT 1
                """,
                (indicator,),
            ).fetchone()

    def _connect(self) -> sqlite3.Connection:
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS macro_indicator_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicator TEXT NOT NULL,
                value_percent TEXT NOT NULL,
                effective_date TEXT,
                effective_from TEXT,
                rate_date TEXT,
                publication_date TEXT,
                volume_rub_billion TEXT,
                trades_count INTEGER,
                participants_count INTEGER,
                calculation_status TEXT,
                period_year INTEGER,
                period_month INTEGER,
                target_percent TEXT,
                source TEXT NOT NULL,
                source_url TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                quality_status TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_macro_indicator_latest
            ON macro_indicator_observations(indicator, fetched_at DESC, id DESC);
            """
        )


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _date_text(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _datetime_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _decimal(value: str) -> Decimal:
    return Decimal(value)


def _optional_decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _optional_date(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
