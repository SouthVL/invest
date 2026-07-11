from __future__ import annotations

from decimal import Decimal

from app.domain.portfolio_all import PortfolioAsset


def group_assets_by_security(assets: list[PortfolioAsset]) -> list[PortfolioAsset]:
    groups: dict[str, list[PortfolioAsset]] = {}
    for index, asset in enumerate(assets):
        key = security_group_key(asset, index)
        groups.setdefault(key, []).append(asset)

    return [merge_security_assets(group) for group in groups.values()]


def security_group_key(asset: PortfolioAsset, index: int) -> str:
    if asset.isin:
        return f"isin:{asset.isin.upper()}"
    if asset.instrument_uid:
        return f"instrument_uid:{asset.instrument_uid}"
    if asset.figi:
        return f"figi:{asset.figi}"
    return f"position:{index}"


def merge_security_assets(assets: list[PortfolioAsset]) -> PortfolioAsset:
    first = assets[0]
    quantity = sum((asset.quantity for asset in assets), Decimal("0"))
    currency = common_currency(assets)
    return PortfolioAsset(
        account_id="",
        instrument_uid=first.instrument_uid,
        position_uid=first.position_uid,
        figi=first.figi,
        ticker=first.ticker,
        instrument_type=first.instrument_type,
        name=first.name,
        isin=first.isin,
        quantity=quantity,
        average_position_price=weighted_price(assets, "average_position_price", quantity, currency),
        current_price=weighted_price(assets, "current_price", quantity, currency),
        price_currency=currency,
    )


def common_currency(assets: list[PortfolioAsset]) -> str | None:
    currencies = {asset.price_currency.upper() for asset in assets if asset.price_currency}
    if len(currencies) == 1:
        return currencies.pop()
    return None


def weighted_price(assets: list[PortfolioAsset], field: str, quantity: Decimal, currency: str | None) -> Decimal | None:
    if quantity == 0 or currency is None:
        return None
    values = [getattr(asset, field) for asset in assets]
    if any(value is None for value in values):
        return None
    if any((asset.price_currency or "").upper() != currency for asset in assets):
        return None
    total = sum((value * asset.quantity for value, asset in zip(values, assets, strict=True)), Decimal("0"))
    return total / quantity
