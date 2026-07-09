from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType
from invest_bonds.adapter import _enum_name
from invest_bonds.money import money_currency, money_to_decimal, quotation_to_decimal
from invest_bonds.sdk_compat import configure_t_invest_sdk


class TInvestCashflowService:
    def __init__(self, client):
        self.client = client
        self._fx_rates: dict[tuple[str, str], Decimal] = {}

    def get_bond_cashflow_events(
        self,
        account_id: str,
        from_date: date,
        to_date: date,
        repeat_floating_last_coupon: bool = False,
        report_currency: str = "RUB",
    ) -> list[CashflowEvent]:
        configure_t_invest_sdk()
        portfolio = self.client.operations.get_portfolio(account_id=account_id)
        events: list[CashflowEvent] = []

        for position in portfolio.positions:
            if (getattr(position, "instrument_type", "") or "").lower() != "bond":
                continue
            events.extend(
                self._get_position_cashflow(
                    position,
                    from_date,
                    to_date,
                    repeat_floating_last_coupon=repeat_floating_last_coupon,
                    report_currency=report_currency,
                )
            )

        return events

    def get_portfolio_cashflow_events(
        self,
        account_id: str,
        from_date: date,
        to_date: date,
        repeat_floating_last_coupon: bool = False,
        report_currency: str = "RUB",
    ) -> list[CashflowEvent]:
        configure_t_invest_sdk()
        portfolio = self.client.operations.get_portfolio(account_id=account_id)
        events: list[CashflowEvent] = []

        for position in portfolio.positions:
            instrument_type = (getattr(position, "instrument_type", "") or "").lower()
            if instrument_type == "bond":
                events.extend(
                    self._get_position_cashflow(
                        position,
                        from_date,
                        to_date,
                        repeat_floating_last_coupon=repeat_floating_last_coupon,
                        report_currency=report_currency,
                    )
                )
            elif instrument_type in {"share", "stock"}:
                events.extend(self._get_share_dividend_cashflow(position, from_date, to_date, report_currency=report_currency))

        return events

    def _get_position_cashflow(
        self,
        position: Any,
        from_date: date,
        to_date: date,
        *,
        repeat_floating_last_coupon: bool = False,
        report_currency: str = "RUB",
    ) -> list[CashflowEvent]:
        from t_tech.invest.schemas import EventType, GetBondEventsRequest, InstrumentIdType

        figi = getattr(position, "figi", "") or None
        position_uid = getattr(position, "instrument_uid", "") or ""
        instrument_id = position_uid or figi or ""
        id_type = InstrumentIdType.INSTRUMENT_ID_TYPE_UID if position_uid else InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI

        bond = self.client.instruments.bond_by(id_type=id_type, id=instrument_id).instrument
        instrument_uid = getattr(bond, "uid", "") or position_uid or figi or ""
        quantity = quotation_to_decimal(getattr(position, "quantity", None)) or Decimal("0")
        is_floating = bool(getattr(bond, "floating_coupon_flag", False))
        should_repeat_floating = repeat_floating_last_coupon and is_floating
        last_floating_coupon_amount = (
            self._last_known_coupon_amount(
                figi=figi or "",
                instrument_uid=instrument_uid,
                before_date=from_date,
            )
            if should_repeat_floating
            else None
        )

        from_dt = _day_start(from_date)
        to_dt = _day_start(to_date)
        coupons_response = self.client.instruments.get_bond_coupons(
            figi=figi or "",
            instrument_id=instrument_uid,
            from_=from_dt,
            to=to_dt,
        )
        bond_events_response = self.client.instruments.get_bond_events(
            GetBondEventsRequest(
                from_=from_dt,
                to=to_dt,
                instrument_id=instrument_uid,
                type=EventType.EVENT_TYPE_UNSPECIFIED,
            )
        )

        events = []
        for coupon in coupons_response.events:
            if _to_date(getattr(coupon, "coupon_date", None)) is None:
                continue
            coupon_amount = money_to_decimal(getattr(coupon, "pay_one_bond", None))
            if should_repeat_floating and _is_missing_coupon_amount(coupon_amount) and last_floating_coupon_amount:
                events.append(
                    self._coupon_event(
                        bond=bond,
                        coupon=coupon,
                        quantity=quantity,
                        amount_override=last_floating_coupon_amount,
                        source=CashflowSource.REPEATED_FLOATING_COUPON,
                        report_currency=report_currency,
                    )
                )
            else:
                source = CashflowSource.FLOATING_COUPON if is_floating else CashflowSource.ACTUAL
                events.append(
                    self._coupon_event(
                        bond=bond,
                        coupon=coupon,
                        quantity=quantity,
                        source=source,
                        report_currency=report_currency,
                    )
                )

        for event in bond_events_response.events:
            cashflow_event = self._bond_event(
                bond=bond,
                event=event,
                quantity=quantity,
                sdk_event_type=EventType,
                report_currency=report_currency,
            )
            if cashflow_event is not None:
                events.append(cashflow_event)

        maturity_event = self._fallback_maturity_event(
            bond=bond,
            quantity=quantity,
            from_date=from_date,
            to_date=to_date,
            report_currency=report_currency,
        )
        if maturity_event and not _has_maturity_event(events, maturity_event.event_date):
            events.append(maturity_event)

        return events

    def _coupon_event(
        self,
        *,
        bond: Any,
        coupon: Any,
        quantity: Decimal,
        amount_override: Decimal | None = None,
        source: CashflowSource = CashflowSource.ACTUAL,
        report_currency: str = "RUB",
    ) -> CashflowEvent:
        amount = amount_override if amount_override is not None else money_to_decimal(getattr(coupon, "pay_one_bond", None)) or Decimal("0")
        payment_currency = _currency(getattr(coupon, "pay_one_bond", None), bond)
        converted_amount = self._convert_money(amount, payment_currency, report_currency)
        converted_total = converted_amount * quantity
        return CashflowEvent(
            instrument_uid=getattr(bond, "uid", ""),
            figi=getattr(bond, "figi", None),
            isin=getattr(bond, "isin", None),
            name=getattr(bond, "name", ""),
            event_date=_to_date(getattr(coupon, "coupon_date", None)) or date.min,
            event_type=CashflowType.COUPON,
            amount_per_bond=converted_amount,
            quantity=quantity,
            total_amount=converted_total,
            currency=report_currency.upper(),
            payment_amount_per_unit=amount,
            payment_total_amount=amount * quantity,
            payment_currency=payment_currency,
            source=source,
        )

    def _last_known_coupon_amount(self, *, figi: str, instrument_uid: str, before_date: date) -> Decimal | None:
        lookback_start = before_date - timedelta(days=366 * 5)
        coupons_response = self.client.instruments.get_bond_coupons(
            figi=figi,
            instrument_id=instrument_uid,
            from_=_day_start(lookback_start),
            to=_day_start(before_date),
        )
        known_coupons: list[tuple[date, Decimal]] = []
        for coupon in coupons_response.events:
            coupon_date = _to_date(getattr(coupon, "coupon_date", None))
            amount = money_to_decimal(getattr(coupon, "pay_one_bond", None))
            if coupon_date is None or coupon_date >= before_date or _is_missing_coupon_amount(amount):
                continue
            known_coupons.append((coupon_date, amount))
        if not known_coupons:
            return None
        return max(known_coupons, key=lambda item: item[0])[1]

    def _get_share_dividend_cashflow(
        self,
        position: Any,
        from_date: date,
        to_date: date,
        *,
        report_currency: str = "RUB",
    ) -> list[CashflowEvent]:
        from t_tech.invest.schemas import InstrumentIdType

        figi = getattr(position, "figi", "") or ""
        position_uid = getattr(position, "instrument_uid", "") or ""
        instrument_id = position_uid or figi
        if not instrument_id:
            return []

        id_type = InstrumentIdType.INSTRUMENT_ID_TYPE_UID if position_uid else InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI
        share = self.client.instruments.share_by(id_type=id_type, id=instrument_id).instrument
        instrument_uid = getattr(share, "uid", "") or position_uid or figi
        quantity = quotation_to_decimal(getattr(position, "quantity", None)) or Decimal("0")
        dividends_response = self.client.instruments.get_dividends(
            figi=figi,
            instrument_id=instrument_uid,
            from_=_day_start(from_date),
            to=_day_start(to_date),
        )

        events: list[CashflowEvent] = []
        for dividend in dividends_response.dividends:
            payment_date = _to_date(getattr(dividend, "payment_date", None))
            if payment_date is None:
                continue
            amount = money_to_decimal(getattr(dividend, "dividend_net", None)) or Decimal("0")
            payment_currency = _currency(getattr(dividend, "dividend_net", None), share)
            converted_amount = self._convert_money(amount, payment_currency, report_currency)
            events.append(
                CashflowEvent(
                    instrument_uid=instrument_uid,
                    figi=getattr(share, "figi", None) or figi,
                    isin=getattr(share, "isin", None),
                    name=getattr(share, "name", "") or getattr(position, "ticker", "") or figi,
                    event_date=payment_date,
                    event_type=CashflowType.DIVIDEND,
                    amount_per_bond=converted_amount,
                    quantity=quantity,
                    total_amount=converted_amount * quantity,
                    currency=report_currency.upper(),
                    payment_amount_per_unit=amount,
                    payment_total_amount=amount * quantity,
                    payment_currency=payment_currency,
                )
            )
        return events

    def _bond_event(
        self,
        *,
        bond: Any,
        event: Any,
        quantity: Decimal,
        sdk_event_type: Any,
        report_currency: str = "RUB",
    ) -> CashflowEvent | None:
        event_date = _to_date(getattr(event, "pay_date", None)) or _to_date(getattr(event, "event_date", None))
        if event_date is None:
            return None

        event_type = getattr(event, "event_type", None)
        if event_type == sdk_event_type.EVENT_TYPE_MTY:
            cashflow_type = CashflowType.MATURITY
            amount = _event_money(event) or money_to_decimal(getattr(bond, "nominal", None)) or Decimal("0")
        elif _is_amortization_event(event):
            cashflow_type = CashflowType.AMORTIZATION
            amount = _event_money(event) or Decimal("0")
        else:
            return None

        payment_currency = _currency(getattr(event, "pay_one_bond", None), bond)
        converted_amount = self._convert_money(amount, payment_currency, report_currency)
        return CashflowEvent(
            instrument_uid=getattr(bond, "uid", ""),
            figi=getattr(bond, "figi", None),
            isin=getattr(bond, "isin", None),
            name=getattr(bond, "name", ""),
            event_date=event_date,
            event_type=cashflow_type,
            amount_per_bond=converted_amount,
            quantity=quantity,
            total_amount=converted_amount * quantity,
            currency=report_currency.upper(),
            payment_amount_per_unit=amount,
            payment_total_amount=amount * quantity,
            payment_currency=payment_currency,
        )

    def _fallback_maturity_event(
        self,
        *,
        bond: Any,
        quantity: Decimal,
        from_date: date,
        to_date: date,
        report_currency: str = "RUB",
    ) -> CashflowEvent | None:
        maturity_date = _to_date(getattr(bond, "maturity_date", None))
        if maturity_date is None or maturity_date < from_date or maturity_date >= to_date:
            return None
        amount = money_to_decimal(getattr(bond, "nominal", None)) or Decimal("0")
        payment_currency = _currency(getattr(bond, "nominal", None), bond)
        converted_amount = self._convert_money(amount, payment_currency, report_currency)
        return CashflowEvent(
            instrument_uid=getattr(bond, "uid", ""),
            figi=getattr(bond, "figi", None),
            isin=getattr(bond, "isin", None),
            name=getattr(bond, "name", ""),
            event_date=maturity_date,
            event_type=CashflowType.MATURITY,
            amount_per_bond=converted_amount,
            quantity=quantity,
            total_amount=converted_amount * quantity,
            currency=report_currency.upper(),
            payment_amount_per_unit=amount,
            payment_total_amount=amount * quantity,
            payment_currency=payment_currency,
        )

    def _convert_money(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        source = from_currency.upper()
        target = to_currency.upper()
        if source == target:
            return amount
        rate = self._fx_rate(source, target)
        return amount * rate

    def _fx_rate(self, from_currency: str, to_currency: str) -> Decimal:
        key = (from_currency.upper(), to_currency.upper())
        if key in self._fx_rates:
            return self._fx_rates[key]
        if key[1] != "RUB":
            raise ValueError(f"FX conversion {key[0]} -> {key[1]} is not supported yet")

        currency_uid = self._currency_uid_for_rub_pair(key[0])
        prices = self.client.market_data.get_last_prices(instrument_id=[currency_uid]).last_prices
        if not prices:
            raise ValueError(f"Could not fetch FX rate for {key[0]} -> RUB")
        rate = quotation_to_decimal(getattr(prices[0], "price", None))
        if rate is None or rate <= Decimal("0"):
            raise ValueError(f"Invalid FX rate for {key[0]} -> RUB")
        self._fx_rates[key] = rate
        return rate

    def _currency_uid_for_rub_pair(self, currency: str) -> str:
        source = currency.upper()
        currencies = self.client.instruments.currencies().instruments
        candidates = []
        for instrument in currencies:
            iso_name = (getattr(instrument, "iso_currency_name", "") or "").upper()
            ticker = (getattr(instrument, "ticker", "") or "").upper()
            payment_currency = (getattr(instrument, "currency", "") or "").upper()
            name = (getattr(instrument, "name", "") or "").upper()
            if payment_currency == "RUB" and (iso_name == source or ticker.startswith(source) or source in name):
                candidates.append(instrument)
        if not candidates:
            raise ValueError(f"Could not find RUB FX instrument for {source}")
        return getattr(candidates[0], "uid", "") or getattr(candidates[0], "figi", "")


def _event_money(event: Any) -> Decimal | None:
    for field in ("pay_one_bond", "money_flow_val"):
        value = money_to_decimal(getattr(event, field, None))
        if value is not None and value != Decimal("0"):
            return value
    return quotation_to_decimal(getattr(event, "value", None))


def _is_amortization_event(event: Any) -> bool:
    text = " ".join(
        [
            _enum_name(getattr(event, "event_type", "")),
            getattr(event, "operation_type", ""),
            getattr(event, "execution", ""),
            getattr(event, "note", ""),
        ]
    ).lower()
    markers = ("amort", "аморт", "погашение части", "частичное погашение")
    return any(marker in text for marker in markers)


def _has_maturity_event(events: list[CashflowEvent], event_date: date) -> bool:
    return any(event.event_type == CashflowType.MATURITY and event.event_date == event_date for event in events)


def _is_missing_coupon_amount(value: Decimal | None) -> bool:
    return value is None or value == Decimal("0")


def _currency(value: Any, bond: Any) -> str:
    currency = money_currency(value) or getattr(bond, "currency", None) or "RUB"
    return currency.upper()


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
