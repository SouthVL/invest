from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from app.analytics.cashflow_forecast import _add_months, build_monthly_cashflow
from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType
from app.reporting.cashflow import CashflowAccountReport, CashflowReport, build_cashflow_report

DEMO_AS_OF = date(2026, 7, 1)
DEMO_GENERATED_AT = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
DEMO_ACCOUNT_LABEL = "demo_account"


def build_demo_cashflow_report(
    *,
    months: int,
    as_of: date = DEMO_AS_OF,
    report_currency: str = "RUB",
) -> CashflowReport:
    if months < 1:
        raise ValueError("--months must be at least 1")
    if report_currency.upper() != "RUB":
        raise ValueError("Demo cashflow currently supports RUB report currency only")

    events = filter_events_for_window(demo_cashflow_events(), as_of=as_of, months=months)
    rows = build_monthly_cashflow(events, start_date=as_of, months=months, currency=report_currency.upper())
    return build_cashflow_report(
        as_of=as_of,
        months=months,
        report_currency=report_currency.upper(),
        account_results=[
            CashflowAccountReport(
                account_label=DEMO_ACCOUNT_LABEL,
                monthly=rows,
                events=events,
            )
        ],
        generated_at=DEMO_GENERATED_AT,
    )


def demo_cashflow_events() -> list[CashflowEvent]:
    return [
        CashflowEvent(
            instrument_uid="demo-gov-fixed",
            figi="DEMOFIGI001",
            isin="DEMO000001",
            name="Demo Government Fixed Bond",
            event_date=date(2026, 7, 15),
            event_type=CashflowType.COUPON,
            amount_per_bond=Decimal("35.00"),
            quantity=Decimal("10"),
            total_amount=Decimal("350.00"),
            currency="RUB",
            payment_amount_per_unit=Decimal("35.00"),
            payment_total_amount=Decimal("350.00"),
            payment_currency="RUB",
            source=CashflowSource.ACTUAL,
        ),
        CashflowEvent(
            instrument_uid="demo-corp-fixed",
            figi="DEMOFIGI002",
            isin="DEMO000002",
            name="Demo Corporate Fixed Bond",
            event_date=date(2026, 8, 10),
            event_type=CashflowType.COUPON,
            amount_per_bond=Decimal("45.00"),
            quantity=Decimal("8"),
            total_amount=Decimal("360.00"),
            currency="RUB",
            payment_amount_per_unit=Decimal("45.00"),
            payment_total_amount=Decimal("360.00"),
            payment_currency="RUB",
            source=CashflowSource.ACTUAL,
        ),
        CashflowEvent(
            instrument_uid="demo-dividend-share",
            figi="DEMOFIGI003",
            isin="DEMO000003",
            name="Demo Dividend Share",
            event_date=date(2026, 8, 25),
            event_type=CashflowType.DIVIDEND,
            amount_per_bond=Decimal("12.00"),
            quantity=Decimal("20"),
            total_amount=Decimal("240.00"),
            currency="RUB",
            payment_amount_per_unit=Decimal("12.00"),
            payment_total_amount=Decimal("240.00"),
            payment_currency="RUB",
            source=CashflowSource.ACTUAL,
        ),
        CashflowEvent(
            instrument_uid="demo-floater",
            figi="DEMOFIGI004",
            isin="DEMO000004",
            name="Demo Key Rate Floater",
            event_date=date(2026, 9, 15),
            event_type=CashflowType.COUPON,
            amount_per_bond=Decimal("42.10"),
            quantity=Decimal("10"),
            total_amount=Decimal("421.00"),
            currency="RUB",
            payment_amount_per_unit=Decimal("42.10"),
            payment_total_amount=Decimal("421.00"),
            payment_currency="RUB",
            source=CashflowSource.FLOATING_COUPON,
        ),
        CashflowEvent(
            instrument_uid="demo-amortizing",
            figi="DEMOFIGI005",
            isin="DEMO000005",
            name="Demo Amortizing Bond",
            event_date=date(2026, 10, 20),
            event_type=CashflowType.AMORTIZATION,
            amount_per_bond=Decimal("200.00"),
            quantity=Decimal("5"),
            total_amount=Decimal("1000.00"),
            currency="RUB",
            payment_amount_per_unit=Decimal("200.00"),
            payment_total_amount=Decimal("1000.00"),
            payment_currency="RUB",
            source=CashflowSource.ACTUAL,
        ),
        CashflowEvent(
            instrument_uid="demo-usd-bond",
            figi="DEMOFIGI006",
            isin="DEMO000006",
            name="Demo USD Bond",
            event_date=date(2026, 11, 5),
            event_type=CashflowType.COUPON,
            amount_per_bond=Decimal("90.00"),
            quantity=Decimal("5"),
            total_amount=Decimal("450.00"),
            currency="RUB",
            payment_amount_per_unit=Decimal("1.00"),
            payment_total_amount=Decimal("5.00"),
            payment_currency="USD",
            source=CashflowSource.ACTUAL,
        ),
        CashflowEvent(
            instrument_uid="demo-floater",
            figi="DEMOFIGI004",
            isin="DEMO000004",
            name="Demo Key Rate Floater",
            event_date=date(2026, 12, 15),
            event_type=CashflowType.COUPON,
            amount_per_bond=Decimal("43.00"),
            quantity=Decimal("10"),
            total_amount=Decimal("430.00"),
            currency="RUB",
            payment_amount_per_unit=Decimal("43.00"),
            payment_total_amount=Decimal("430.00"),
            payment_currency="RUB",
            source=CashflowSource.REPEATED_FLOATING_COUPON,
        ),
        CashflowEvent(
            instrument_uid="demo-maturity",
            figi="DEMOFIGI007",
            isin="DEMO000007",
            name="Demo Maturing Bond",
            event_date=date(2027, 1, 20),
            event_type=CashflowType.MATURITY,
            amount_per_bond=Decimal("1000.00"),
            quantity=Decimal("3"),
            total_amount=Decimal("3000.00"),
            currency="RUB",
            payment_amount_per_unit=Decimal("1000.00"),
            payment_total_amount=Decimal("3000.00"),
            payment_currency="RUB",
            source=CashflowSource.ACTUAL,
        ),
    ]


def filter_events_for_window(events: list[CashflowEvent], *, as_of: date, months: int) -> list[CashflowEvent]:
    window_end = _add_months(date(as_of.year, as_of.month, 1), months)
    return [event for event in events if as_of <= event.event_date < window_end]
