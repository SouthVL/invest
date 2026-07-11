from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from app.domain.portfolio_all import PortfolioAsset, PortfolioSnapshot
from invest_bonds.money import money_currency, money_to_decimal, quotation_to_decimal
from invest_bonds.sdk_compat import configure_t_invest_sdk

logger = logging.getLogger(__name__)


def normalize_instrument_type(*values: Any) -> str:
    for value in values:
        normalized = _normalize_instrument_type_value(value)
        if normalized:
            return normalized
    return ""


def _normalize_instrument_type_value(value: Any) -> str:
    if value is None:
        return ""

    name = getattr(value, "name", None)
    text = str(name or value).strip().lower()
    if not text:
        return ""

    text = text.replace("-", "_").replace(" ", "_")
    if "." in text:
        text = text.rsplit(".", maxsplit=1)[-1]
    if text.startswith("instrument_type_"):
        text = text.removeprefix("instrument_type_")

    aliases = {
        "0": "",
        "unspecified": "",
        "1": "bond",
        "bond": "bond",
        "bonds": "bond",
        "облигация": "bond",
        "облигации": "bond",
        "2": "share",
        "share": "share",
        "shares": "share",
        "stock": "share",
        "stocks": "share",
        "equity": "share",
        "акция": "share",
        "акции": "share",
        "3": "currency",
        "currency": "currency",
        "currencies": "currency",
        "4": "etf",
        "etf": "etf",
        "fund": "etf",
        "funds": "etf",
        "5": "futures",
        "future": "futures",
        "futures": "futures",
        "7": "option",
        "option": "option",
        "options": "option",
    }
    return aliases.get(text, text)


class TInvestPortfolioAllService:
    def __init__(self, client):
        self.client = client

    def get_portfolio_snapshot(self, account_id: str, as_of: date) -> PortfolioSnapshot:
        configure_t_invest_sdk()
        portfolio = self.client.operations.get_portfolio(account_id=account_id)
        assets = [
            self._asset_from_position(account_id, position)
            for position in portfolio.positions
            if (quotation_to_decimal(getattr(position, "quantity", None)) or Decimal("0")) > Decimal("0")
        ]
        return PortfolioSnapshot(
            account_id=account_id,
            fetched_at=datetime.now(timezone.utc),
            as_of=as_of,
            assets=assets,
            total_value=money_to_decimal(getattr(portfolio, "total_amount_portfolio", None)),
            total_value_currency=money_currency(getattr(portfolio, "total_amount_portfolio", None)),
        )

    def _asset_from_position(self, account_id: str, position: Any) -> PortfolioAsset:
        instrument = self._instrument(position)
        current_price = getattr(position, "current_price", None)
        average_price = getattr(position, "average_position_price", None)
        return PortfolioAsset(
            account_id=account_id,
            instrument_uid=getattr(position, "instrument_uid", "") or getattr(instrument, "uid", "") or getattr(position, "figi", ""),
            position_uid=getattr(position, "position_uid", "") or getattr(instrument, "position_uid", ""),
            figi=getattr(position, "figi", "") or getattr(instrument, "figi", ""),
            ticker=getattr(position, "ticker", "") or getattr(instrument, "ticker", ""),
            instrument_type=normalize_instrument_type(
                getattr(instrument, "instrument_kind", None),
                getattr(instrument, "instrument_type", None),
                getattr(position, "instrument_type", None),
            ),
            name=getattr(instrument, "name", "") or getattr(position, "ticker", "") or getattr(position, "figi", ""),
            isin=getattr(instrument, "isin", ""),
            quantity=quotation_to_decimal(getattr(position, "quantity", None)) or Decimal("0"),
            average_position_price=money_to_decimal(average_price),
            current_price=money_to_decimal(current_price),
            price_currency=money_currency(current_price) or money_currency(average_price),
        )

    def _instrument(self, position: Any) -> Any:
        from t_tech.invest.schemas import InstrumentIdType

        instrument_uid = getattr(position, "instrument_uid", "") or ""
        figi = getattr(position, "figi", "") or ""
        try:
            if instrument_uid:
                return self.client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
                    id=instrument_uid,
                ).instrument
            return self.client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                id=figi,
            ).instrument
        except Exception as exc:
            logger.warning("Could not fetch instrument metadata for %s: %s", instrument_uid or figi, exc)
            return _FallbackInstrument(figi=figi, ticker=getattr(position, "ticker", ""))


class _FallbackInstrument:
    def __init__(self, *, figi: str = "", ticker: str = "") -> None:
        self.figi = figi
        self.ticker = ticker
        self.uid = ""
        self.position_uid = ""
        self.instrument_kind = None
        self.instrument_type = ""
        self.name = ticker or figi
        self.isin = ""
