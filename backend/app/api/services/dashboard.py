from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from app.reporting.portfolio import PortfolioReport
from app.reporting.serializers.cashflow_json import iso_datetime, money
from app.reporting.serializers.portfolio_json import asset_to_dict


def build_dashboard(
    *,
    portfolio: PortfolioReport,
    mode: Literal["demo", "real"],
    account_label: str,
    cashflow_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    assets = [asset for account in portfolio.accounts for asset in account.assets]
    total_value = total_portfolio_value(portfolio)
    total_amount = total_value["amount"] if total_value else None
    total_currency = total_value["currency"] if total_value else None
    warnings = list(portfolio.warnings)
    if total_value is None and assets:
        warnings.append("Portfolio total value is unavailable because comparable currency data is missing.")

    positions = sorted(assets, key=position_sort_key, reverse=True)

    return {
        "schema_version": "1.0",
        "mode": mode,
        "portfolio": {
            "status": "fresh",
            "account_label": account_label,
            "total_value": total_value,
            "daily_yield": None,
            "expected_yield": None,
            "updated_at": iso_datetime(portfolio.generated_at),
            "period": portfolio.as_of.isoformat(),
        },
        "allocation": allocation_by_type(assets, total_amount, total_currency),
        "positions_preview": [asset_to_dict(asset) for asset in positions[:5]],
        "cashflow_summary": cashflow_summary,
        "macro": {
            "status": "unavailable",
            "key_rate": None,
            "inflation_yoy": None,
            "updated_at": None,
        },
        "warnings": warnings,
    }


def total_portfolio_value(portfolio: PortfolioReport) -> dict[str, str] | None:
    account_totals = [
        (account.total_value, account.total_value_currency)
        for account in portfolio.accounts
        if account.total_value is not None and account.total_value_currency
    ]
    if account_totals:
        currencies = {currency.upper() for _, currency in account_totals}
        if len(currencies) == 1:
            currency = currencies.pop()
            return money(sum((amount for amount, _ in account_totals), Decimal("0")), currency)
        return None

    assets = [asset for account in portfolio.accounts for asset in account.assets]
    totals: dict[str, Decimal] = {}
    for asset in assets:
        value = asset_market_value(asset)
        if value is None or not asset.price_currency:
            continue
        currency = asset.price_currency.upper()
        totals[currency] = totals.get(currency, Decimal("0")) + value
    if len(totals) != 1:
        return None
    currency, amount = next(iter(totals.items()))
    return money(amount, currency)


def allocation_by_type(assets: list[Any], total_amount: str | None, total_currency: str | None) -> list[dict[str, Any]]:
    if total_amount is None or total_currency is None:
        return []
    total_value = Decimal(total_amount)
    totals: dict[str, Decimal] = {}
    for asset in assets:
        value = asset_market_value(asset)
        if value is None or (asset.price_currency or "").upper() != total_currency.upper():
            continue
        instrument_type = asset.instrument_type or "unknown"
        totals[instrument_type] = totals.get(instrument_type, Decimal("0")) + value

    return [
        {
            "type": instrument_type,
            "value": money(value, total_currency),
            "share_percent": decimal_percent(value, total_value),
        }
        for instrument_type, value in sorted(totals.items())
    ]


def asset_market_value(asset: Any) -> Decimal | None:
    if asset.current_price is None:
        return None
    return asset.current_price * asset.quantity


def position_sort_key(asset: Any) -> tuple[int, Decimal]:
    value = asset_market_value(asset)
    if value is None:
        return (0, Decimal("0"))
    return (1, value)


def decimal_percent(part: Decimal, total: Decimal) -> str | None:
    if total == 0:
        return None
    return format((part / total * Decimal("100")).quantize(Decimal("0.01")), "f")
