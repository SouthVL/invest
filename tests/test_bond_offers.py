from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.analytics.bond_offers import filter_and_sort_offers, offer_status
from app.domain.bond_offer import BondOfferEvent, OfferEventType, OfferStatus
from app.t_invest.bond_offers import TInvestBondOfferService, classify_offer_event


def offer(name: str, offer_date: date, days_until: int, status: OfferStatus = OfferStatus.OK) -> BondOfferEvent:
    return BondOfferEvent(
        instrument_uid=f"uid-{name}",
        isin=f"ISIN-{name}",
        name=name,
        offer_date=offer_date,
        event_type=OfferEventType.OFFER,
        quantity=Decimal("10"),
        days_until_offer=days_until,
        status=status,
    )


def test_detect_future_offer_event() -> None:
    class EventType:
        EVENT_TYPE_CALL = 2

    event = SimpleNamespace(event_type=EventType.EVENT_TYPE_CALL, operation_type="", execution="", note="")

    assert classify_offer_event(event, EventType) == OfferEventType.CALL


def test_ignore_past_offer_events() -> None:
    offers = filter_and_sort_offers(
        [offer("Past", date(2026, 4, 1), -26)],
        as_of=date(2026, 4, 27),
        days=180,
    )

    assert offers == []


def test_correct_days_until_offer_calculation() -> None:
    assert (date(2026, 6, 1) - date(2026, 5, 12)).days == 20


def test_warning_status_when_days_within_warning_window() -> None:
    assert offer_status(date(2026, 6, 1), date(2026, 5, 12), warning_days=45) == OfferStatus.WARNING


def test_ok_status_otherwise() -> None:
    assert offer_status(date(2026, 8, 1), date(2026, 5, 12), warning_days=45) == OfferStatus.OK


def test_sorting_by_nearest_date_then_name() -> None:
    offers = filter_and_sort_offers(
        [
            offer("Bond B", date(2026, 8, 1), 81),
            offer("Bond C", date(2026, 6, 1), 20),
            offer("Bond A", date(2026, 6, 1), 20),
        ],
        as_of=date(2026, 5, 12),
        days=180,
    )

    assert [item.name for item in offers] == ["Bond A", "Bond C", "Bond B"]


def test_unknown_event_types_handled_safely() -> None:
    class EventType:
        EVENT_TYPE_CALL = 2

    event = SimpleNamespace(event_type=999, operation_type="offer window", execution="", note="")

    assert classify_offer_event(event, EventType) == OfferEventType.OFFER


def test_empty_offers_list_handled_correctly() -> None:
    assert filter_and_sort_offers([], as_of=date(2026, 5, 12), days=180) == []


def test_api_failure_for_one_bond_does_not_stop_processing() -> None:
    class FakeOperations:
        def get_portfolio(self, account_id: str):
            return SimpleNamespace(
                positions=[
                    SimpleNamespace(figi="bad", instrument_uid="bad", instrument_type="bond", quantity=SimpleNamespace(units=1, nano=0)),
                    SimpleNamespace(figi="ok", instrument_uid="ok", instrument_type="bond", quantity=SimpleNamespace(units=1, nano=0)),
                ]
            )

    class FakeInstruments:
        def bond_by(self, **kwargs):
            if kwargs["id"] == "bad":
                raise RuntimeError("boom")
            return SimpleNamespace(instrument=SimpleNamespace(uid="ok", figi="ok", isin="RU000B", name="Bond B"))

        def get_bond_events(self, request):
            return SimpleNamespace(
                events=[
                    SimpleNamespace(
                        event_type=2,
                        event_date=date(2026, 6, 1),
                        pay_date=None,
                        operation_type="",
                        execution="",
                        note="",
                    )
                ]
            )

    class FakeClient:
        operations = FakeOperations()
        instruments = FakeInstruments()

    offers = TInvestBondOfferService(FakeClient()).get_upcoming_offers(
        account_id="account",
        from_date=date(2026, 5, 12),
        to_date=date(2026, 12, 1),
        warning_days=45,
    )

    assert len(offers) == 1
    assert offers[0].name == "Bond B"
    assert offers[0].status == OfferStatus.WARNING
