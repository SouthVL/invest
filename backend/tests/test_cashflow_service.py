from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.domain.cashflow import CashflowType
from app.t_invest.cashflow import TInvestCashflowService


def quotation(value: int) -> SimpleNamespace:
    return SimpleNamespace(units=value, nano=0)


def money(value: int, currency: str = "rub") -> SimpleNamespace:
    return SimpleNamespace(units=value, nano=0, currency=currency)


def test_portfolio_cashflow_includes_share_dividends() -> None:
    class FakeOperations:
        def get_portfolio(self, account_id: str) -> SimpleNamespace:
            return SimpleNamespace(
                positions=[
                    SimpleNamespace(
                        instrument_type="share",
                        figi="BBG000B9XRY4",
                        instrument_uid="share-uid",
                        ticker="SBER",
                        quantity=quotation(10),
                    )
                ]
            )

    class FakeInstruments:
        def share_by(self, **kwargs) -> SimpleNamespace:
            return SimpleNamespace(
                instrument=SimpleNamespace(
                    uid="share-uid",
                    figi="BBG000B9XRY4",
                    isin="RU0009029540",
                    name="Sber",
                    currency="rub",
                )
            )

        def get_dividends(self, **kwargs) -> SimpleNamespace:
            return SimpleNamespace(
                dividends=[
                    SimpleNamespace(
                        payment_date=datetime(2026, 7, 15, tzinfo=timezone.utc),
                        dividend_net=money(35),
                    )
                ]
            )

    client = SimpleNamespace(operations=FakeOperations(), instruments=FakeInstruments())

    events = TInvestCashflowService(client).get_portfolio_cashflow_events(
        account_id="account-1",
        from_date=date(2026, 7, 1),
        to_date=date(2026, 8, 1),
    )

    assert len(events) == 1
    assert events[0].event_type == CashflowType.DIVIDEND
    assert events[0].event_date == date(2026, 7, 15)
    assert events[0].amount_per_bond == Decimal("35")
    assert events[0].quantity == Decimal("10")
    assert events[0].total_amount == Decimal("350")


def test_portfolio_cashflow_converts_foreign_dividends_to_report_currency() -> None:
    class FakeOperations:
        def get_portfolio(self, account_id: str) -> SimpleNamespace:
            return SimpleNamespace(
                positions=[
                    SimpleNamespace(
                        instrument_type="share",
                        figi="US0378331005",
                        instrument_uid="share-uid",
                        ticker="AAPL",
                        quantity=quotation(2),
                    )
                ]
            )

    class FakeInstruments:
        def share_by(self, **kwargs) -> SimpleNamespace:
            return SimpleNamespace(
                instrument=SimpleNamespace(
                    uid="share-uid",
                    figi="US0378331005",
                    isin="US0378331005",
                    name="Apple",
                    currency="usd",
                )
            )

        def get_dividends(self, **kwargs) -> SimpleNamespace:
            return SimpleNamespace(
                dividends=[
                    SimpleNamespace(
                        payment_date=datetime(2026, 7, 15, tzinfo=timezone.utc),
                        dividend_net=money(1, currency="usd"),
                    )
                ]
            )

        def currencies(self) -> SimpleNamespace:
            return SimpleNamespace(
                instruments=[
                    SimpleNamespace(
                        uid="usd-rub-uid",
                        figi="USD000UTSTOM",
                        ticker="USD000UTSTOM",
                        iso_currency_name="usd",
                        currency="rub",
                        name="USD/RUB",
                    )
                ]
            )

    class FakeMarketData:
        def get_last_prices(self, **kwargs) -> SimpleNamespace:
            return SimpleNamespace(last_prices=[SimpleNamespace(price=quotation(90))])

    client = SimpleNamespace(operations=FakeOperations(), instruments=FakeInstruments(), market_data=FakeMarketData())

    events = TInvestCashflowService(client).get_portfolio_cashflow_events(
        account_id="account-1",
        from_date=date(2026, 7, 1),
        to_date=date(2026, 8, 1),
        report_currency="RUB",
    )

    assert events[0].payment_currency == "USD"
    assert events[0].payment_amount_per_unit == Decimal("1")
    assert events[0].amount_per_bond == Decimal("90")
    assert events[0].total_amount == Decimal("180")
    assert events[0].currency == "RUB"
