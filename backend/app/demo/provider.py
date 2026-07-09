from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from app.analytics.cashflow_forecast import _add_months, build_monthly_cashflow
from app.domain.bond_offer import BondOfferEvent, OfferEventType, OfferStatus
from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType
from app.domain.portfolio_all import PortfolioAsset
from app.reporting.cashflow import CashflowAccountReport, CashflowReport, build_cashflow_report
from app.reporting.offers import OffersAccountReport, OffersReport, build_offers_report
from app.reporting.portfolio import PortfolioAccountReport, PortfolioReport, build_portfolio_report

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


def build_demo_offers_report(
    *,
    as_of: date = DEMO_AS_OF,
    days: int = 180,
    warning_days: int = 45,
) -> OffersReport:
    if days < 1:
        raise ValueError("--days must be at least 1")
    if warning_days < 0:
        raise ValueError("--warning-days must be non-negative")

    to_date = date.fromordinal(as_of.toordinal() + days)
    offers = [offer for offer in demo_offer_events(as_of=as_of, warning_days=warning_days) if as_of <= offer.offer_date <= to_date]
    return build_offers_report(
        as_of=as_of,
        days=days,
        warning_days=warning_days,
        account_results=[
            OffersAccountReport(
                account_label=DEMO_ACCOUNT_LABEL,
                offers=offers,
            )
        ],
        generated_at=DEMO_GENERATED_AT,
    )


def build_demo_portfolio_report(
    *,
    as_of: date = DEMO_AS_OF,
) -> PortfolioReport:
    return build_portfolio_report(
        as_of=as_of,
        account_results=[
            PortfolioAccountReport(
                account_label=DEMO_ACCOUNT_LABEL,
                assets=demo_portfolio_assets(),
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


def demo_portfolio_assets() -> list[PortfolioAsset]:
    return [
        PortfolioAsset(
            account_id=DEMO_ACCOUNT_LABEL,
            instrument_uid="demo-gov-fixed",
            figi="DEMOFIGI001",
            ticker="DGOV",
            instrument_type="bond",
            name="Demo Government Fixed Bond",
            isin="DEMO000001",
            quantity=Decimal("10"),
            average_position_price=Decimal("985.00"),
            current_price=Decimal("1002.50"),
            price_currency="RUB",
        ),
        PortfolioAsset(
            account_id=DEMO_ACCOUNT_LABEL,
            instrument_uid="demo-dividend-share",
            figi="DEMOFIGI003",
            ticker="DSHR",
            instrument_type="share",
            name="Demo Dividend Share",
            isin="DEMO000003",
            quantity=Decimal("20"),
            average_position_price=Decimal("145.00"),
            current_price=Decimal("152.00"),
            price_currency="RUB",
        ),
        PortfolioAsset(
            account_id=DEMO_ACCOUNT_LABEL,
            instrument_uid="demo-usd-bond",
            figi="DEMOFIGI006",
            ticker="DUSD",
            instrument_type="bond",
            name="Demo USD Bond",
            isin="DEMO000006",
            quantity=Decimal("5"),
            average_position_price=Decimal("900.00"),
            current_price=Decimal("910.00"),
            price_currency="RUB",
        ),
    ]


def demo_offer_events(*, as_of: date = DEMO_AS_OF, warning_days: int = 45) -> list[BondOfferEvent]:
    return [
        demo_offer(
            instrument_uid="demo-corp-fixed",
            figi="DEMOFIGI002",
            isin="DEMO000002",
            name="Demo Corporate Fixed Bond",
            offer_date=date(2026, 9, 20),
            event_type=OfferEventType.CALL,
            quantity=Decimal("8"),
            as_of=as_of,
            warning_days=warning_days,
        ),
        demo_offer(
            instrument_uid="demo-amortizing",
            figi="DEMOFIGI005",
            isin="DEMO000005",
            name="Demo Amortizing Bond",
            offer_date=date(2026, 12, 1),
            event_type=OfferEventType.OFFER,
            quantity=Decimal("5"),
            as_of=as_of,
            warning_days=warning_days,
        ),
    ]


def demo_offer(
    *,
    instrument_uid: str,
    figi: str,
    isin: str,
    name: str,
    offer_date: date,
    event_type: OfferEventType,
    quantity: Decimal,
    as_of: date,
    warning_days: int,
) -> BondOfferEvent:
    days_until_offer = offer_date.toordinal() - as_of.toordinal()
    if days_until_offer < 0:
        status = OfferStatus.EXPIRED
    elif days_until_offer <= warning_days:
        status = OfferStatus.WARNING
    else:
        status = OfferStatus.OK
    return BondOfferEvent(
        instrument_uid=instrument_uid,
        figi=figi,
        isin=isin,
        name=name,
        offer_date=offer_date,
        event_type=event_type,
        quantity=quantity,
        days_until_offer=days_until_offer,
        status=status,
    )


def filter_events_for_window(events: list[CashflowEvent], *, as_of: date, months: int) -> list[CashflowEvent]:
    window_end = _add_months(date(as_of.year, as_of.month, 1), months)
    return [event for event in events if as_of <= event.event_date < window_end]
