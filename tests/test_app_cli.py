from datetime import date
from decimal import Decimal

from rich.console import Console

from app.cli import (
    combine_monthly_cashflows,
    render_cashflow,
    render_cashflow_details,
    render_floating_scenario_details,
    render_maturity_details,
)
from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType, MonthlyCashflow
from app.domain.floating_scenarios import CouponSource, FloatingScenarioCouponEvent, ScenarioType


def test_render_cashflow_uses_custom_account_title() -> None:
    console = Console(record=True, width=120)

    render_cashflow(
        [
            MonthlyCashflow(
                month="2026-05",
                coupons=Decimal("10"),
                amortizations=Decimal("20"),
                maturities=Decimal("30"),
                total=Decimal("60"),
            )
        ],
        console,
        title="Monthly bond cashflow forecast - Broker (account-1)",
    )

    rendered = console.export_text()
    assert "Monthly bond cashflow forecast - Broker (account-1)" in rendered
    assert "2026-05" in rendered
    assert "Fixed coupons" in rendered
    assert "Floaters" in rendered
    assert "Dividends" in rendered


def test_render_maturity_details_shows_bond_level_maturity_info() -> None:
    console = Console(record=True, width=160)

    render_maturity_details(
        [
            CashflowEvent(
                instrument_uid="uid-1",
                figi="figi-1",
                isin="RU000A",
                name="Bond A",
                event_date=date(2026, 6, 10),
                event_type=CashflowType.MATURITY,
                amount_per_bond=Decimal("1000"),
                quantity=Decimal("5"),
                total_amount=Decimal("5000"),
                currency="RUB",
            )
        ],
        console,
        title="Maturity details - Broker (account-1)",
    )

    rendered = console.export_text()
    assert "Maturity details - Broker (account-1)" in rendered
    assert "10.06.2026" in rendered
    assert "RU000A" in rendered
    assert "5 000.00 ₽" in rendered


def test_render_maturity_details_skips_table_when_no_maturities() -> None:
    console = Console(record=True, width=120)

    render_maturity_details([], console)

    assert console.export_text() == ""


def test_render_cashflow_details_shows_future_payments_for_window() -> None:
    console = Console(record=True, width=180)

    render_cashflow_details(
        [
            CashflowEvent(
                instrument_uid="uid-1",
                figi="figi-1",
                isin="RU000A",
                name="Bond A",
                event_date=date(2026, 6, 10),
                event_type=CashflowType.COUPON,
                amount_per_bond=Decimal("42.50"),
                quantity=Decimal("5"),
                total_amount=Decimal("212.50"),
                currency="RUB",
                source=CashflowSource.REPEATED_FLOATING_COUPON,
            ),
            CashflowEvent(
                instrument_uid="uid-2",
                figi="figi-2",
                isin="RU000B",
                name="Bond B",
                event_date=date(2026, 8, 1),
                event_type=CashflowType.COUPON,
                amount_per_bond=Decimal("1"),
                quantity=Decimal("1"),
                total_amount=Decimal("1"),
                currency="RUB",
            ),
            CashflowEvent(
                instrument_uid="uid-3",
                figi="figi-3",
                isin="RU000C",
                name="Share C",
                event_date=date(2026, 6, 20),
                event_type=CashflowType.DIVIDEND,
                amount_per_bond=Decimal("12.25"),
                quantity=Decimal("3"),
                total_amount=Decimal("36.75"),
                currency="RUB",
            ),
        ],
        console,
        start_date=date(2026, 6, 1),
        months=2,
        title="Future bond cashflow details - Broker (account-1)",
    )

    rendered = console.export_text()
    assert "Future bond cashflow details - Broker (account-1)" in rendered
    assert "10.06.2026" in rendered
    assert "Bond A" in rendered
    assert "Share C" in rendered
    assert "dividend" in rendered
    assert "floating: last coupon" in rendered
    assert "Bond B" not in rendered


def test_combine_monthly_cashflows_sums_all_accounts_by_month() -> None:
    combined = combine_monthly_cashflows(
        [
            [
                MonthlyCashflow(
                    month="2026-05",
                    coupons=Decimal("10"),
                    fixed_coupons=Decimal("6"),
                    floating_coupons=Decimal("4"),
                    dividends=Decimal("4"),
                    amortizations=Decimal("20"),
                    maturities=Decimal("30"),
                    total=Decimal("64"),
                )
            ],
            [
                MonthlyCashflow(
                    month="2026-05",
                    coupons=Decimal("1.50"),
                    fixed_coupons=Decimal("1"),
                    floating_coupons=Decimal("0.50"),
                    dividends=Decimal("0.25"),
                    amortizations=Decimal("2.50"),
                    maturities=Decimal("3.50"),
                    total=Decimal("7.75"),
                )
            ],
        ]
    )

    assert combined[0].month == "2026-05"
    assert combined[0].coupons == Decimal("11.50")
    assert combined[0].fixed_coupons == Decimal("7")
    assert combined[0].floating_coupons == Decimal("4.50")
    assert combined[0].dividends == Decimal("4.25")
    assert combined[0].amortizations == Decimal("22.50")
    assert combined[0].maturities == Decimal("33.50")
    assert combined[0].total == Decimal("71.75")


def test_render_floating_scenario_details_shows_base_coupon() -> None:
    console = Console(record=True, width=180)

    render_floating_scenario_details(
        [
            FloatingScenarioCouponEvent(
                instrument_uid="uid-1",
                isin="RU000A",
                name="Bond A",
                coupon_date=date(2026, 6, 15),
                scenario=ScenarioType.CURRENT_COUPON,
                source=CouponSource.FORECAST,
                base_coupon_per_bond=Decimal("42.50"),
                annual_coupon_rate_percent=Decimal("17.05"),
                nominal=Decimal("1000"),
                quantity=Decimal("10"),
                coupon_period_days=91,
                coupon_per_bond=Decimal("42.50"),
                total_coupon=Decimal("425.00"),
            )
        ],
        console,
    )

    rendered = console.export_text()
    assert "Base coupon" in rendered
    assert "CURRENT_COUPON" in rendered
    assert "42.50 ₽" in rendered
