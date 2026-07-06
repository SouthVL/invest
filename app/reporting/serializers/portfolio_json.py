from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from app.domain.portfolio_all import PortfolioAsset
from app.reporting.portfolio import PortfolioReport
from app.reporting.serializers.cashflow_json import decimal_text, iso_datetime, money


def portfolio_report_to_dict(report: PortfolioReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "report_type": report.report_type,
        "generated_at": iso_datetime(report.generated_at),
        "as_of": report.as_of.isoformat(),
        "accounts": [
            {
                "account_label": account.account_label,
                **({"account_id": account.account_id} if account.account_id else {}),
                "assets": [asset_to_dict(asset) for asset in account.assets],
            }
            for account in report.accounts
        ],
        "summary": report.summary,
        "warnings": report.warnings,
        "data_quality": report.data_quality,
    }


def portfolio_report_to_json(report: PortfolioReport) -> str:
    return json.dumps(portfolio_report_to_dict(report), ensure_ascii=False, indent=2) + "\n"


def asset_to_dict(asset: PortfolioAsset) -> dict[str, Any]:
    return {
        "instrument_uid": asset.instrument_uid,
        "position_uid": asset.position_uid,
        "figi": asset.figi,
        "ticker": asset.ticker,
        "instrument_type": asset.instrument_type,
        "instrument_name": asset.name,
        "isin": asset.isin,
        "quantity": decimal_text(asset.quantity),
        "average_position_price": optional_money(asset.average_position_price, asset.price_currency),
        "current_price": optional_money(asset.current_price, asset.price_currency),
        "market_value": optional_money(
            asset.current_price * asset.quantity if asset.current_price is not None else None, asset.price_currency
        ),
        "source_status": "actual",
    }


def optional_money(amount: Decimal | None, currency: str | None) -> dict[str, str] | None:
    if amount is None:
        return None
    return money(amount, currency or "unknown")
