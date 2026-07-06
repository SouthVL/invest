import json
from datetime import date, datetime, timezone
from decimal import Decimal

from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType, MonthlyCashflow
from app.reporting.cashflow import CashflowAccountReport, build_cashflow_report
from app.reporting.serializers.cashflow_csv import cashflow_events_to_csv, cashflow_monthly_to_csv
from app.reporting.serializers.cashflow_json import cashflow_report_to_json


def sample_report(include_account_id: bool = False):
    account = CashflowAccountReport(
        account_label="account_1",
        account_id="real-account-id" if include_account_id else None,
        monthly=[
            MonthlyCashflow(
                month="2026-07",
                fixed_coupons=Decimal("100.10"),
                floating_coupons=Decimal("50.20"),
                dividends=Decimal("10.30"),
                amortizations=Decimal("0"),
                maturities=Decimal("1000"),
                coupons=Decimal("150.30"),
                total=Decimal("1160.60"),
                currency="RUB",
            )
        ],
        events=[
            CashflowEvent(
                instrument_uid="uid-1",
                figi="figi-1",
                isin="RU000A",
                name="Demo Floater",
                event_date=date(2026, 7, 15),
                event_type=CashflowType.COUPON,
                amount_per_bond=Decimal("50.20"),
                quantity=Decimal("1"),
                total_amount=Decimal("50.20"),
                currency="RUB",
                payment_amount_per_unit=Decimal("0.50"),
                payment_total_amount=Decimal("0.50"),
                payment_currency="USD",
                source=CashflowSource.REPEATED_FLOATING_COUPON,
            )
        ],
    )
    return build_cashflow_report(
        as_of=date(2026, 7, 1),
        months=1,
        report_currency="RUB",
        account_results=[account],
        generated_at=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
    )


def test_cashflow_json_has_stable_top_level_keys_and_decimal_strings() -> None:
    payload = json.loads(cashflow_report_to_json(sample_report()))

    assert list(payload.keys()) == [
        "schema_version",
        "report_type",
        "generated_at",
        "as_of",
        "months",
        "report_currency",
        "accounts",
        "summary",
        "warnings",
        "data_quality",
    ]
    assert payload["schema_version"] == "1.0"
    assert payload["generated_at"] == "2026-07-01T12:00:00Z"
    assert payload["summary"]["total"] == {"amount": "1160.60", "currency": "RUB"}
    assert isinstance(payload["summary"]["total"]["amount"], str)


def test_cashflow_json_does_not_include_account_id_by_default() -> None:
    payload = json.loads(cashflow_report_to_json(sample_report()))

    assert "account_id" not in payload["accounts"][0]


def test_cashflow_json_can_include_account_id_explicitly() -> None:
    payload = json.loads(cashflow_report_to_json(sample_report(include_account_id=True)))

    assert payload["accounts"][0]["account_id"] == "real-account-id"


def test_cashflow_json_marks_estimated_and_capital_return_flags() -> None:
    event = json.loads(cashflow_report_to_json(sample_report()))["accounts"][0]["events"][0]

    assert event["source_status"] == "estimated"
    assert event["source"] == "floating: last coupon"
    assert event["payment_amount_per_unit"] == {"amount": "0.50", "currency": "USD"}
    assert event["is_capital_return"] is False


def test_cashflow_monthly_csv_has_stable_header() -> None:
    csv_text = cashflow_monthly_to_csv(sample_report())

    assert csv_text.splitlines()[0] == (
        "account_label,month,fixed_coupons_amount,floating_coupons_amount,dividends_amount,"
        "amortizations_amount,maturities_amount,total_amount,currency"
    )
    assert "account_1,2026-07,100.10,50.20,10.30,0,1000,1160.60,RUB" in csv_text


def test_cashflow_events_csv_has_stable_header_and_source_status() -> None:
    csv_text = cashflow_events_to_csv(sample_report())

    assert csv_text.splitlines()[0] == (
        "account_label,payment_date,payment_month,payment_type,instrument_name,isin,figi,quantity,"
        "amount_per_unit,total_amount,currency,payment_amount_per_unit,payment_total_amount,payment_currency,"
        "source,source_status,scenario_id,is_capital_return"
    )
    assert "floating: last coupon,estimated" in csv_text
