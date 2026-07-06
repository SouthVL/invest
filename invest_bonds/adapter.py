from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from invest_bonds.models import (
    AccountSummary,
    BondCoupon,
    BondEvent,
    BondEventType,
    BondHolding,
    BondInstrument,
    BondPosition,
    BondSnapshot,
)
from invest_bonds.money import money_currency, money_to_decimal, quotation_to_decimal
from invest_bonds.rules import analyze_bond
from invest_bonds.sdk_compat import configure_t_invest_sdk


def _enum_name(value: Any) -> str:
    name = getattr(value, "name", None)
    if name:
        return str(name)
    return str(value)


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


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _day_end(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


class TInvestAdapter:
    """Small read-only wrapper around the T-Invest SDK."""

    def __init__(self, token: str) -> None:
        self._token = token

    def get_accounts(self) -> list[AccountSummary]:
        configure_t_invest_sdk()
        from t_tech.invest import Client

        with Client(self._token) as client:
            response = client.users.get_accounts()
            return [
                AccountSummary(
                    id=account.id,
                    name=getattr(account, "name", ""),
                    type=_enum_name(getattr(account, "type", "")),
                    status=_enum_name(getattr(account, "status", "")),
                    access_level=_enum_name(getattr(account, "access_level", "")),
                )
                for account in response.accounts
            ]

    def fetch_snapshot(self, *, account_id: str, as_of: date, lookahead_days: int) -> BondSnapshot:
        configure_t_invest_sdk()
        from t_tech.invest import Client

        with Client(self._token) as client:
            portfolio = client.operations.get_portfolio(account_id=account_id)
            holdings = [
                self._build_holding(client=client, position=position, as_of=as_of, lookahead_days=lookahead_days)
                for position in portfolio.positions
                if (getattr(position, "instrument_type", "") or "").lower() == "bond"
            ]
        return BondSnapshot(
            account_id=account_id,
            fetched_at=datetime.now(timezone.utc),
            as_of=as_of,
            holdings=holdings,
        )

    def _build_holding(self, *, client: Any, position: Any, as_of: date, lookahead_days: int) -> BondHolding:
        configure_t_invest_sdk()
        from t_tech.invest.schemas import EventType, GetBondEventsRequest, InstrumentIdType

        instrument_id = getattr(position, "instrument_uid", "") or getattr(position, "figi", "")
        id_type = (
            InstrumentIdType.INSTRUMENT_ID_TYPE_UID
            if getattr(position, "instrument_uid", "")
            else InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI
        )
        bond_response = client.instruments.bond_by(id_type=id_type, id=instrument_id)
        bond = bond_response.instrument
        uid = getattr(bond, "uid", "") or getattr(position, "instrument_uid", "") or getattr(position, "figi", "")

        from_date = _day_start(as_of)
        to_date = _day_end(as_of + timedelta(days=lookahead_days))

        coupons_response = client.instruments.get_bond_coupons(
            figi=getattr(position, "figi", ""),
            instrument_id=uid,
            from_=from_date,
            to=to_date,
        )

        event_request = GetBondEventsRequest(
            from_=from_date,
            to=to_date,
            instrument_id=uid,
            type=EventType.EVENT_TYPE_UNSPECIFIED,
        )
        events_response = client.instruments.get_bond_events(event_request)

        instrument = self._to_instrument(uid=uid, bond=bond)
        bond_position = self._to_position(uid=uid, position=position)
        coupons = [self._to_coupon(uid=uid, coupon=coupon) for coupon in coupons_response.events if _to_date(coupon.coupon_date)]
        events = [self._to_event(uid=uid, event=event, sdk_event_type=EventType) for event in events_response.events]
        analysis = analyze_bond(instrument=instrument, coupons=coupons, events=events, as_of=as_of)
        return BondHolding(
            instrument=instrument,
            position=bond_position,
            coupons=coupons,
            events=events,
            analysis=analysis,
        )

    def _to_instrument(self, *, uid: str, bond: Any) -> BondInstrument:
        nominal = getattr(bond, "nominal", None)
        return BondInstrument(
            uid=uid,
            position_uid=getattr(bond, "position_uid", ""),
            figi=getattr(bond, "figi", ""),
            isin=getattr(bond, "isin", ""),
            name=getattr(bond, "name", ""),
            nominal=money_to_decimal(nominal),
            nominal_currency=money_currency(nominal),
            maturity_date=_to_date(getattr(bond, "maturity_date", None)),
            coupon_quantity_per_year=getattr(bond, "coupon_quantity_per_year", None),
            floating_coupon_flag=bool(getattr(bond, "floating_coupon_flag", False)),
            perpetual_flag=bool(getattr(bond, "perpetual_flag", False)),
            amortization_flag=bool(getattr(bond, "amortization_flag", False)),
        )

    def _to_position(self, *, uid: str, position: Any) -> BondPosition:
        current_price = getattr(position, "current_price", None)
        average_price = getattr(position, "average_position_price", None)
        return BondPosition(
            figi=getattr(position, "figi", ""),
            ticker=getattr(position, "ticker", ""),
            instrument_uid=uid,
            position_uid=getattr(position, "position_uid", ""),
            quantity=quotation_to_decimal(getattr(position, "quantity", None)) or 0,
            quantity_lots=quotation_to_decimal(getattr(position, "quantity_lots", None)) or 0,
            average_position_price=money_to_decimal(average_price),
            current_price=money_to_decimal(current_price),
            price_currency=money_currency(current_price) or money_currency(average_price),
            expected_yield=quotation_to_decimal(getattr(position, "expected_yield", None)),
        )

    def _to_coupon(self, *, uid: str, coupon: Any) -> BondCoupon:
        amount = getattr(coupon, "pay_one_bond", None)
        return BondCoupon(
            instrument_uid=uid,
            figi=getattr(coupon, "figi", ""),
            coupon_date=_to_date(getattr(coupon, "coupon_date", None)) or date.min,
            pay_one_bond=money_to_decimal(amount),
            currency=money_currency(amount),
            coupon_type=_enum_name(getattr(coupon, "coupon_type", "")),
            coupon_period=getattr(coupon, "coupon_period", None),
        )

    def _to_event(self, *, uid: str, event: Any, sdk_event_type: Any) -> BondEvent:
        event_type = BondEventType.OTHER
        sdk_value = getattr(event, "event_type", None)
        if sdk_value == sdk_event_type.EVENT_TYPE_CPN:
            event_type = BondEventType.COUPON
        elif sdk_value == sdk_event_type.EVENT_TYPE_CALL:
            event_type = BondEventType.CALL
        elif sdk_value == sdk_event_type.EVENT_TYPE_MTY:
            event_type = BondEventType.MATURITY

        amount = getattr(event, "pay_one_bond", None)
        return BondEvent(
            instrument_uid=uid,
            event_type=event_type,
            event_date=_to_date(getattr(event, "event_date", None)),
            pay_date=_to_date(getattr(event, "pay_date", None)),
            amount=money_to_decimal(amount),
            currency=money_currency(amount),
            value=quotation_to_decimal(getattr(event, "value", None)),
            note=getattr(event, "note", ""),
        )
