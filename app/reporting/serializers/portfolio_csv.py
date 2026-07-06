from __future__ import annotations

import csv
from io import StringIO

from app.domain.portfolio_all import PortfolioAsset
from app.reporting.portfolio import PortfolioReport
from app.reporting.serializers.cashflow_json import decimal_text

PORTFOLIO_HEADER = [
    "account_label",
    "instrument_name",
    "isin",
    "figi",
    "ticker",
    "instrument_type",
    "quantity",
    "average_position_price",
    "current_price",
    "market_value",
    "price_currency",
    "source_status",
]


def portfolio_to_csv(report: PortfolioReport) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(PORTFOLIO_HEADER)
    for account in report.accounts:
        for asset in account.assets:
            writer.writerow(asset_row(account.account_label, asset))
    return output.getvalue()


def asset_row(account_label: str, asset: PortfolioAsset) -> list[str]:
    market_value = asset.current_price * asset.quantity if asset.current_price is not None else None
    return [
        account_label,
        asset.name,
        asset.isin,
        asset.figi,
        asset.ticker,
        asset.instrument_type,
        decimal_text(asset.quantity),
        decimal_text(asset.average_position_price) if asset.average_position_price is not None else "",
        decimal_text(asset.current_price) if asset.current_price is not None else "",
        decimal_text(market_value) if market_value is not None else "",
        (asset.price_currency or "").upper(),
        "actual",
    ]
