import json
from datetime import date, datetime, timezone
from decimal import Decimal

from app.domain.bond_offer import BondOfferEvent, OfferEventType, OfferStatus
from app.reporting.offers import OffersAccountReport, build_offers_report
from app.reporting.serializers.offers_json import offers_report_to_json


def offer() -> BondOfferEvent:
    return BondOfferEvent(
        instrument_uid="uid-1",
        figi="figi-1",
        isin="RU000A",
        name="Demo Callable Bond",
        offer_date=date(2026, 7, 20),
        event_type=OfferEventType.CALL,
        quantity=Decimal("10"),
        days_until_offer=19,
        status=OfferStatus.WARNING,
    )


def report(include_account_id: bool = False):
    return build_offers_report(
        as_of=date(2026, 7, 1),
        days=180,
        warning_days=45,
        account_results=[
            OffersAccountReport(
                account_label="account_1",
                account_id="real-account-id" if include_account_id else None,
                offers=[offer()],
            )
        ],
        generated_at=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
    )


def test_offers_json_has_stable_keys_and_decimal_strings() -> None:
    payload = json.loads(offers_report_to_json(report()))

    assert list(payload.keys()) == [
        "schema_version",
        "report_type",
        "generated_at",
        "as_of",
        "days",
        "warning_days",
        "accounts",
        "summary",
        "warnings",
        "data_quality",
    ]
    assert payload["schema_version"] == "1.0"
    assert payload["accounts"][0]["offers"][0]["quantity"] == "10"
    assert payload["accounts"][0]["offers"][0]["source_status"] == "actual"


def test_offers_json_hides_account_id_by_default() -> None:
    payload = json.loads(offers_report_to_json(report()))

    assert "account_id" not in payload["accounts"][0]


def test_offers_json_can_include_account_id_explicitly() -> None:
    payload = json.loads(offers_report_to_json(report(include_account_id=True)))

    assert payload["accounts"][0]["account_id"] == "real-account-id"


def test_offers_report_summary_counts_warnings() -> None:
    payload = json.loads(offers_report_to_json(report()))

    assert payload["summary"]["total_offers"] == 1
    assert payload["summary"]["within_30_days"] == 1
    assert payload["summary"]["warnings_count"] == 1
    assert payload["warnings"] == ["Demo Callable Bond: call in 19 days"]
