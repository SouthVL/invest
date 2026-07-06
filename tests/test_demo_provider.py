import json
from datetime import date
from decimal import Decimal

from app.demo.provider import DEMO_AS_OF, build_demo_cashflow_report, build_demo_offers_report
from app.domain.bond_offer import OfferEventType
from app.domain.cashflow import CashflowType
from app.reporting.serializers.cashflow_json import cashflow_report_to_json


def test_demo_cashflow_is_deterministic() -> None:
    first = cashflow_report_to_json(build_demo_cashflow_report(months=12))
    second = cashflow_report_to_json(build_demo_cashflow_report(months=12))

    assert first == second


def test_demo_cashflow_uses_fixed_as_of_by_default() -> None:
    report = build_demo_cashflow_report(months=12)

    assert report.as_of == DEMO_AS_OF
    assert report.generated_at.isoformat() == "2026-07-01T12:00:00+00:00"


def test_demo_cashflow_contains_core_event_types() -> None:
    report = build_demo_cashflow_report(months=12)
    event_types = {event.event_type for event in report.accounts[0].events}

    assert CashflowType.COUPON in event_types
    assert CashflowType.DIVIDEND in event_types
    assert CashflowType.AMORTIZATION in event_types
    assert CashflowType.MATURITY in event_types


def test_demo_cashflow_contains_foreign_currency_payment() -> None:
    report = build_demo_cashflow_report(months=12)
    usd_event = next(event for event in report.accounts[0].events if event.name == "Demo USD Bond")

    assert usd_event.payment_currency == "USD"
    assert usd_event.payment_amount_per_unit == Decimal("1.00")
    assert usd_event.currency == "RUB"


def test_demo_cashflow_json_has_estimated_warning() -> None:
    payload = json.loads(cashflow_report_to_json(build_demo_cashflow_report(months=12)))

    assert payload["as_of"] == "2026-07-01"
    assert payload["summary"]["estimated_total"] == {"amount": "430.00", "currency": "RUB"}
    assert payload["warnings"] == ["Some cashflow items are estimates and are not confirmed payments."]


def test_demo_cashflow_can_use_custom_as_of() -> None:
    report = build_demo_cashflow_report(months=1, as_of=date(2026, 8, 1))

    assert report.as_of == date(2026, 8, 1)
    assert report.accounts[0].monthly[0].month == "2026-08"


def test_demo_cashflow_events_are_limited_to_forecast_window() -> None:
    report = build_demo_cashflow_report(months=1)

    assert [event.name for event in report.accounts[0].events] == ["Demo Government Fixed Bond"]
    assert report.summary.total == Decimal("350.00")


def test_demo_offers_are_deterministic_and_offline() -> None:
    first = build_demo_offers_report(days=180)
    second = build_demo_offers_report(days=180)

    assert first == second
    assert first.as_of == DEMO_AS_OF
    assert first.accounts[0].offers[0].event_type == OfferEventType.CALL
    assert first.summary["total_offers"] == 2
