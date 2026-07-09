from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from app.domain.bond_position import BondCouponScheduleItem
from app.domain.floating_scenarios import FloatingScenarioBondPosition
from invest_bonds.money import money_currency, money_to_decimal, quotation_to_decimal
from invest_bonds.sdk_compat import configure_t_invest_sdk

logger = logging.getLogger(__name__)


class TInvestFloatingScenarioService:
    def __init__(self, client):
        self.client = client

    def get_floating_scenario_positions(
        self,
        account_id: str,
        from_date: date,
        to_date: date,
    ) -> list[FloatingScenarioBondPosition]:
        configure_t_invest_sdk()
        portfolio = self.client.operations.get_portfolio(account_id=account_id)
        positions: list[FloatingScenarioBondPosition] = []
        for position in portfolio.positions:
            if (getattr(position, "instrument_type", "") or "").lower() != "bond":
                continue
            candidate = self._build_position(position, from_date, to_date)
            if candidate is not None:
                positions.append(candidate)
        return positions

    def _build_position(self, position: Any, from_date: date, to_date: date) -> FloatingScenarioBondPosition | None:
        from t_tech.invest.schemas import InstrumentIdType

        figi = getattr(position, "figi", "") or None
        position_uid = getattr(position, "instrument_uid", "") or ""
        instrument_id = position_uid or figi or ""
        id_type = InstrumentIdType.INSTRUMENT_ID_TYPE_UID if position_uid else InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI
        bond = self.client.instruments.bond_by(id_type=id_type, id=instrument_id).instrument
        uid = getattr(bond, "uid", "") or position_uid or figi or ""
        coupons_response = self.client.instruments.get_bond_coupons(
            figi=figi or "",
            instrument_id=uid,
            from_=_day_start(from_date),
            to=_day_start(to_date),
        )
        coupons = [self._coupon_item(coupon, bond) for coupon in coupons_response.events if _to_date(getattr(coupon, "coupon_date", None))]
        if not bool(getattr(bond, "floating_coupon_flag", False)):
            return None

        if not any(coupon.coupon_amount is not None and coupon.coupon_amount > Decimal("0") for coupon in coupons):
            logger.warning("Skipping floating bond without known coupon: %s %s", getattr(bond, "isin", ""), getattr(bond, "name", ""))
            return None

        return FloatingScenarioBondPosition(
            instrument_uid=uid,
            figi=getattr(bond, "figi", None) or figi,
            isin=getattr(bond, "isin", ""),
            name=getattr(bond, "name", ""),
            quantity=quotation_to_decimal(getattr(position, "quantity", None)) or Decimal("0"),
            nominal=money_to_decimal(getattr(bond, "nominal", None)) or Decimal("0"),
            currency=(money_currency(getattr(bond, "nominal", None)) or getattr(bond, "currency", None) or "RUB").upper(),
            coupons=coupons,
        )

    def _coupon_item(self, coupon: Any, bond: Any) -> BondCouponScheduleItem:
        amount = money_to_decimal(getattr(coupon, "pay_one_bond", None))
        if amount == Decimal("0"):
            amount = None
        return BondCouponScheduleItem(
            coupon_date=_to_date(getattr(coupon, "coupon_date", None)) or date.min,
            coupon_period_days=getattr(coupon, "coupon_period", None),
            coupon_amount=amount,
            currency=(money_currency(getattr(coupon, "pay_one_bond", None)) or getattr(bond, "currency", None) or "RUB").upper(),
        )


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.year <= 1970:
            return None
        return value.date()
    if isinstance(value, date):
        if value.year <= 1970:
            return None
        return value
    return None
