from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.domain.macro_indicators import AnnualInflationValue, CurrentMacroSnapshot, KeyRateValue, RuoniaValue
from app.reporting.serializers.cashflow_json import decimal_text


def macro_snapshot_to_dict(snapshot: CurrentMacroSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "report_type": snapshot.report_type,
        "generated_at": iso_datetime(snapshot.generated_at),
        "status": macro_status(snapshot),
        "key_rate": key_rate_to_dict(snapshot.key_rate),
        "ruonia": ruonia_to_dict(snapshot.ruonia),
        "annual_inflation": annual_inflation_to_dict(snapshot.annual_inflation),
        "warnings": snapshot.warnings,
    }


def macro_status(snapshot: CurrentMacroSnapshot) -> str:
    if snapshot.key_rate is None and snapshot.ruonia is None and snapshot.annual_inflation is None:
        return "unavailable"
    if snapshot.key_rate is None or snapshot.ruonia is None or snapshot.annual_inflation is None:
        return "partial"
    return "fresh"


def key_rate_to_dict(value: KeyRateValue | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "value_percent": decimal_percent(value.value_percent),
        "effective_date": value.effective_date.isoformat(),
        "effective_from": value.effective_from.isoformat() if value.effective_from else None,
        "source": value.source,
        "source_url": value.source_url,
        "fetched_at": iso_datetime(value.fetched_at),
        "quality_status": value.quality_status,
    }


def ruonia_to_dict(value: RuoniaValue | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "value_percent": decimal_percent(value.value_percent),
        "rate_date": value.rate_date.isoformat(),
        "publication_date": value.publication_date.isoformat(),
        "volume_rub_billion": decimal_percent(value.volume_rub_billion) if value.volume_rub_billion is not None else None,
        "trades_count": value.trades_count,
        "participants_count": value.participants_count,
        "calculation_status": value.calculation_status,
        "source": value.source,
        "source_url": value.source_url,
        "fetched_at": iso_datetime(value.fetched_at),
        "quality_status": value.quality_status,
    }


def annual_inflation_to_dict(value: AnnualInflationValue | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "value_percent_yoy": decimal_percent(value.value_percent_yoy),
        "period": f"{value.period_year:04d}-{value.period_month:02d}",
        "target_percent": decimal_percent(value.target_percent) if value.target_percent is not None else None,
        "source": value.source,
        "source_url": value.source_url,
        "fetched_at": iso_datetime(value.fetched_at),
        "quality_status": value.quality_status,
    }


def decimal_percent(value: Decimal) -> str:
    return decimal_text(value)


def iso_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

