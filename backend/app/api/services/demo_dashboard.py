from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.demo.provider import build_demo_cashflow_report, build_demo_portfolio_report
from app.reporting.serializers.cashflow_json import iso_datetime, money
from app.reporting.serializers.portfolio_json import asset_to_dict


def build_demo_dashboard() -> dict[str, Any]:
    portfolio = build_demo_portfolio_report()
    cashflow = build_demo_cashflow_report(months=12)
    assets = [asset for account in portfolio.accounts for asset in account.assets]
    total_value = sum(
        (asset.current_price * asset.quantity for asset in assets if asset.current_price is not None),
        Decimal("0"),
    )
    positions = sorted(assets, key=lambda asset: (asset.current_price or Decimal("0")) * asset.quantity, reverse=True)

    return {
        "schema_version": "1.0",
        "mode": "demo",
        "portfolio": {
            "status": "fresh",
            "account_label": "demo_account",
            "total_value": money(total_value, "RUB"),
            "daily_yield": None,
            "expected_yield": None,
            "updated_at": iso_datetime(portfolio.generated_at),
            "period": portfolio.as_of.isoformat(),
        },
        "allocation": allocation_by_type(assets, total_value),
        "positions_preview": [asset_to_dict(asset) for asset in positions[:5]],
        "cashflow_summary": {
            "period": {
                "as_of": cashflow.as_of.isoformat(),
                "months": cashflow.months,
            },
            "updated_at": iso_datetime(cashflow.generated_at),
            "total": money(cashflow.summary.total, cashflow.summary.currency),
            "actual_total": money(cashflow.summary.actual_total, cashflow.summary.currency),
            "estimated_total": money(cashflow.summary.estimated_total, cashflow.summary.currency),
            "unknown_count": cashflow.summary.unknown_count,
        },
        "macro": {
            "status": "unavailable",
            "key_rate": None,
            "inflation_yoy": None,
            "updated_at": None,
        },
        "warnings": cashflow.warnings + portfolio.warnings,
    }


def allocation_by_type(assets: list[Any], total_value: Decimal) -> list[dict[str, Any]]:
    totals: dict[str, Decimal] = {}
    for asset in assets:
        if asset.current_price is None:
            continue
        instrument_type = asset.instrument_type or "unknown"
        totals[instrument_type] = totals.get(instrument_type, Decimal("0")) + asset.current_price * asset.quantity

    return [
        {
            "type": instrument_type,
            "value": money(value, "RUB"),
            "share_percent": decimal_percent(value, total_value),
        }
        for instrument_type, value in sorted(totals.items())
    ]


def decimal_percent(part: Decimal, total: Decimal) -> str | None:
    if total == 0:
        return None
    return format((part / total * Decimal("100")).quantize(Decimal("0.01")), "f")
