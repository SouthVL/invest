from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.portfolio_all import PortfolioAsset
from app.reporting.cashflow import SCHEMA_VERSION


class PortfolioAccountReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_label: str
    account_id: str | None = None
    assets: list[PortfolioAsset] = Field(default_factory=list)


class PortfolioReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = SCHEMA_VERSION
    report_type: str = "portfolio"
    generated_at: datetime
    as_of: date
    accounts: list[PortfolioAccountReport]
    summary: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    data_quality: dict[str, Any] = Field(default_factory=dict)


def build_portfolio_report(
    *,
    as_of: date,
    account_results: list[PortfolioAccountReport],
    generated_at: datetime | None = None,
) -> PortfolioReport:
    assets = [asset for account in account_results for asset in account.assets]
    unknown_price_count = sum(1 for asset in assets if asset.current_price is None)
    warnings = []
    if unknown_price_count:
        warnings.append("Some portfolio assets do not have current price data.")

    return PortfolioReport(
        generated_at=generated_at or datetime.now(timezone.utc),
        as_of=as_of,
        accounts=account_results,
        summary={
            "account_count": len(account_results),
            "asset_count": len(assets),
            "instrument_types": instrument_type_counts(assets),
            "market_value_by_currency": market_value_by_currency(assets),
            "unknown_price_count": unknown_price_count,
        },
        warnings=warnings,
        data_quality={
            "account_count": len(account_results),
            "asset_count": len(assets),
            "source_status": "actual",
        },
    )


def instrument_type_counts(assets: list[PortfolioAsset]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for asset in assets:
        key = asset.instrument_type or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def market_value_by_currency(assets: list[PortfolioAsset]) -> list[dict[str, str]]:
    totals: dict[str, Decimal] = {}
    for asset in assets:
        if asset.current_price is None:
            continue
        currency = (asset.price_currency or "unknown").upper()
        totals[currency] = totals.get(currency, Decimal("0")) + asset.current_price * asset.quantity
    return [{"currency": currency, "amount": format(amount, "f")} for currency, amount in sorted(totals.items())]
