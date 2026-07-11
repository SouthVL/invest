from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.application.macro_indicators import CachedCurrentMacroIndicatorsProvider, daily_refresh_due, monthly_fifth_refresh_due
from app.domain.macro_indicators import AnnualInflationValue, KeyRateValue, RuoniaValue
from app.integrations.cbr.current_indicators import parse_annual_inflation, parse_key_rate, parse_ruonia
from app.storage.macro_indicators import MacroIndicatorsRepository


FETCHED_AT = datetime(2026, 7, 10, 10, 0, tzinfo=UTC)


def test_parse_key_rate_from_cbr_table_text() -> None:
    value = parse_key_rate("<table><tr><td>10.07.2026</td><td>14,25</td></tr></table>", fetched_at=FETCHED_AT)

    assert value.value_percent == Decimal("14.25")
    assert value.effective_date.isoformat() == "2026-07-10"
    assert value.effective_from is None
    assert value.source == "bank_of_russia"
    assert value.fetched_at == FETCHED_AT


def test_parse_ruonia_from_cbr_table_text() -> None:
    value = parse_ruonia(
        """
        <table>
          <tr>
            <td>08.07.2026</td><td>14,43</td><td>1 000,50</td>
            <td>100</td><td>25</td><td>09.07.2026</td>
          </tr>
        </table>
        """,
        fetched_at=FETCHED_AT,
    )

    assert value.value_percent == Decimal("14.43")
    assert value.rate_date.isoformat() == "2026-07-08"
    assert value.publication_date.isoformat() == "2026-07-09"
    assert value.volume_rub_billion == Decimal("1000.50")
    assert value.trades_count == 100
    assert value.participants_count == 25


def test_parse_annual_inflation_from_cbr_table_text() -> None:
    value = parse_annual_inflation("<tr><td>05.2026</td><td>14,50</td><td>5,31</td><td>4,00</td></tr>", fetched_at=FETCHED_AT)

    assert value.value_percent_yoy == Decimal("5.31")
    assert value.period_year == 2026
    assert value.period_month == 5
    assert value.target_percent == Decimal("4.00")
    assert value.source == "rosstat_via_bank_of_russia"


def test_macro_indicators_repository_round_trips_values(tmp_path) -> None:
    repo = MacroIndicatorsRepository(tmp_path / "invest.db")
    key_rate = KeyRateValue(
        value_percent=Decimal("14.25"),
        effective_date=datetime(2026, 7, 10, tzinfo=UTC).date(),
        effective_from=None,
        source="bank_of_russia",
        source_url="https://www.cbr.ru/hd_base/keyrate/",
        fetched_at=FETCHED_AT,
        quality_status="actual",
    )
    ruonia = RuoniaValue(
        value_percent=Decimal("14.43"),
        rate_date=datetime(2026, 7, 9, tzinfo=UTC).date(),
        publication_date=datetime(2026, 7, 10, tzinfo=UTC).date(),
        volume_rub_billion=Decimal("673.42"),
        trades_count=61,
        participants_count=20,
        calculation_status=None,
        source="bank_of_russia",
        source_url="https://www.cbr.ru/hd_base/ruonia/dynamics/",
        fetched_at=FETCHED_AT,
        quality_status="actual",
    )
    inflation = AnnualInflationValue(
        value_percent_yoy=Decimal("5.31"),
        period_year=2026,
        period_month=5,
        target_percent=Decimal("4.00"),
        source="rosstat_via_bank_of_russia",
        source_url="https://www.cbr.ru/hd_base/infl/",
        fetched_at=FETCHED_AT,
        quality_status="actual",
    )

    repo.save_key_rate(key_rate)
    repo.save_ruonia(ruonia)
    repo.save_annual_inflation(inflation)

    assert repo.count_rows() == 3
    assert repo.latest_key_rate() == key_rate
    assert repo.latest_ruonia() == ruonia
    assert repo.latest_annual_inflation() == inflation


def test_macro_refresh_rules_use_monthly_fifth_and_daily_cadence() -> None:
    assert monthly_fifth_refresh_due(None, datetime(2026, 7, 10, tzinfo=UTC).date()) is True
    assert monthly_fifth_refresh_due(datetime(2026, 6, 6, tzinfo=UTC), datetime(2026, 7, 4, tzinfo=UTC).date()) is False
    assert monthly_fifth_refresh_due(datetime(2026, 6, 6, tzinfo=UTC), datetime(2026, 7, 5, tzinfo=UTC).date()) is True
    assert monthly_fifth_refresh_due(datetime(2026, 7, 5, tzinfo=UTC), datetime(2026, 7, 10, tzinfo=UTC).date()) is False
    assert daily_refresh_due(datetime(2026, 7, 9, tzinfo=UTC), datetime(2026, 7, 10, tzinfo=UTC).date()) is True
    assert daily_refresh_due(datetime(2026, 7, 10, tzinfo=UTC), datetime(2026, 7, 10, tzinfo=UTC).date()) is False


def test_cached_macro_provider_uses_database_until_monthly_fifth_rule_is_due(tmp_path) -> None:
    repo = MacroIndicatorsRepository(tmp_path / "invest.db")
    repo.save_key_rate(
        KeyRateValue(
            value_percent=Decimal("14.25"),
            effective_date=datetime(2026, 6, 10, tzinfo=UTC).date(),
            effective_from=None,
            source="bank_of_russia",
            source_url="https://www.cbr.ru/hd_base/keyrate/",
            fetched_at=datetime(2026, 6, 6, tzinfo=UTC),
            quality_status="actual",
        )
    )
    upstream = CountingProvider()
    provider = CachedCurrentMacroIndicatorsProvider(
        upstream=upstream,
        repository=repo,
        now=lambda: datetime(2026, 7, 4, tzinfo=UTC),
    )

    value = provider.get_key_rate()

    assert value.value_percent == Decimal("14.25")
    assert value.quality_status == "cached"
    assert upstream.key_rate_calls == 0


def test_cached_macro_provider_refreshes_monthly_values_on_or_after_fifth(tmp_path) -> None:
    repo = MacroIndicatorsRepository(tmp_path / "invest.db")
    repo.save_annual_inflation(
        AnnualInflationValue(
            value_percent_yoy=Decimal("5.10"),
            period_year=2026,
            period_month=4,
            target_percent=Decimal("4.00"),
            source="rosstat_via_bank_of_russia",
            source_url="https://www.cbr.ru/hd_base/infl/",
            fetched_at=datetime(2026, 6, 6, tzinfo=UTC),
            quality_status="actual",
        )
    )
    upstream = CountingProvider()
    provider = CachedCurrentMacroIndicatorsProvider(
        upstream=upstream,
        repository=repo,
        now=lambda: datetime(2026, 7, 5, tzinfo=UTC),
    )

    value = provider.get_latest_annual_inflation()

    assert value.value_percent_yoy == Decimal("5.31")
    assert value.quality_status == "actual"
    assert upstream.inflation_calls == 1
    assert repo.count_rows() == 2


def test_cached_macro_provider_refreshes_ruonia_daily(tmp_path) -> None:
    repo = MacroIndicatorsRepository(tmp_path / "invest.db")
    repo.save_ruonia(
        RuoniaValue(
            value_percent=Decimal("14.40"),
            rate_date=datetime(2026, 7, 8, tzinfo=UTC).date(),
            publication_date=datetime(2026, 7, 9, tzinfo=UTC).date(),
            source="bank_of_russia",
            source_url="https://www.cbr.ru/hd_base/ruonia/dynamics/",
            fetched_at=datetime(2026, 7, 9, tzinfo=UTC),
            quality_status="actual",
        )
    )
    upstream = CountingProvider()
    provider = CachedCurrentMacroIndicatorsProvider(
        upstream=upstream,
        repository=repo,
        now=lambda: datetime(2026, 7, 10, tzinfo=UTC),
    )

    value = provider.get_latest_ruonia()

    assert value.value_percent == Decimal("14.43")
    assert value.quality_status == "actual"
    assert upstream.ruonia_calls == 1


def test_cached_macro_provider_returns_stale_database_value_when_due_refresh_fails(tmp_path) -> None:
    repo = MacroIndicatorsRepository(tmp_path / "invest.db")
    repo.save_key_rate(
        KeyRateValue(
            value_percent=Decimal("14.25"),
            effective_date=datetime(2026, 6, 10, tzinfo=UTC).date(),
            effective_from=None,
            source="bank_of_russia",
            source_url="https://www.cbr.ru/hd_base/keyrate/",
            fetched_at=datetime(2026, 6, 6, tzinfo=UTC),
            quality_status="actual",
        )
    )
    provider = CachedCurrentMacroIndicatorsProvider(
        upstream=FailingProvider(),
        repository=repo,
        now=lambda: datetime(2026, 7, 5, tzinfo=UTC),
    )

    value = provider.get_key_rate()

    assert value.value_percent == Decimal("14.25")
    assert value.quality_status == "stale"


def test_macro_current_endpoint_returns_safe_snapshot_without_network(monkeypatch, tmp_path) -> None:
    class StubProvider:
        def get_key_rate(self) -> KeyRateValue:
            return KeyRateValue(
                value_percent=Decimal("14.25"),
                effective_date=datetime(2026, 7, 10, tzinfo=UTC).date(),
                effective_from=None,
                source="bank_of_russia",
                source_url="https://www.cbr.ru/hd_base/keyrate/",
                fetched_at=FETCHED_AT,
                quality_status="actual",
            )

        def get_latest_ruonia(self) -> RuoniaValue:
            return RuoniaValue(
                value_percent=Decimal("14.43"),
                rate_date=datetime(2026, 7, 8, tzinfo=UTC).date(),
                publication_date=datetime(2026, 7, 9, tzinfo=UTC).date(),
                source="bank_of_russia",
                source_url="https://www.cbr.ru/hd_base/ruonia/dynamics/",
                fetched_at=FETCHED_AT,
                quality_status="actual",
            )

        def get_latest_annual_inflation(self) -> AnnualInflationValue:
            return AnnualInflationValue(
                value_percent_yoy=Decimal("5.31"),
                period_year=2026,
                period_month=5,
                target_percent=Decimal("4.00"),
                source="rosstat_via_bank_of_russia",
                source_url="https://www.cbr.ru/hd_base/infl/",
                fetched_at=FETCHED_AT,
                quality_status="actual",
            )

    monkeypatch.setenv("SOUTH_INVEST_DB_PATH", str(tmp_path / "invest.db"))
    monkeypatch.setattr("app.api.routes.macro.CbrCurrentIndicatorsProvider", StubProvider)
    client = TestClient(create_app())

    response = client.get("/api/v1/macro/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "fresh"
    assert payload["key_rate"]["value_percent"] == "14.25"
    assert payload["ruonia"]["rate_date"] == "2026-07-08"
    assert payload["annual_inflation"]["period"] == "2026-05"


def test_macro_current_endpoint_returns_partial_snapshot_without_strict(monkeypatch, tmp_path) -> None:
    class PartialProvider:
        def get_key_rate(self) -> KeyRateValue:
            raise RuntimeError("transport unavailable")

        def get_latest_ruonia(self) -> RuoniaValue:
            raise RuntimeError("transport unavailable")

        def get_latest_annual_inflation(self) -> AnnualInflationValue:
            return AnnualInflationValue(
                value_percent_yoy=Decimal("5.31"),
                period_year=2026,
                period_month=5,
                target_percent=None,
                source="rosstat_via_bank_of_russia",
                source_url="https://www.cbr.ru/hd_base/infl/",
                fetched_at=FETCHED_AT,
                quality_status="actual",
            )

    monkeypatch.setenv("SOUTH_INVEST_DB_PATH", str(tmp_path / "invest.db"))
    monkeypatch.setattr("app.api.routes.macro.CbrCurrentIndicatorsProvider", PartialProvider)
    client = TestClient(create_app())

    response = client.get("/api/v1/macro/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["key_rate"] is None
    assert payload["ruonia"] is None
    assert payload["annual_inflation"]["value_percent_yoy"] == "5.31"
    assert payload["warnings"][:2] == [
        "Key rate could not be loaded from Bank of Russia.",
        "RUONIA could not be loaded from Bank of Russia.",
    ]


def test_macro_current_endpoint_strict_requires_all_indicators(monkeypatch, tmp_path) -> None:
    class EmptyProvider:
        def get_key_rate(self) -> KeyRateValue:
            raise RuntimeError("transport unavailable")

        def get_latest_ruonia(self) -> RuoniaValue:
            raise RuntimeError("transport unavailable")

        def get_latest_annual_inflation(self) -> AnnualInflationValue:
            raise RuntimeError("transport unavailable")

    monkeypatch.setenv("SOUTH_INVEST_DB_PATH", str(tmp_path / "invest.db"))
    monkeypatch.setattr("app.api.routes.macro.CbrCurrentIndicatorsProvider", EmptyProvider)
    client = TestClient(create_app())

    response = client.get("/api/v1/macro/current", params={"strict": "true"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Current macro indicators are incomplete."}


class CountingProvider:
    def __init__(self) -> None:
        self.key_rate_calls = 0
        self.ruonia_calls = 0
        self.inflation_calls = 0

    def get_key_rate(self) -> KeyRateValue:
        self.key_rate_calls += 1
        return KeyRateValue(
            value_percent=Decimal("14.00"),
            effective_date=datetime(2026, 7, 10, tzinfo=UTC).date(),
            effective_from=None,
            source="bank_of_russia",
            source_url="https://www.cbr.ru/hd_base/keyrate/",
            fetched_at=FETCHED_AT,
            quality_status="actual",
        )

    def get_latest_ruonia(self) -> RuoniaValue:
        self.ruonia_calls += 1
        return RuoniaValue(
            value_percent=Decimal("14.43"),
            rate_date=datetime(2026, 7, 9, tzinfo=UTC).date(),
            publication_date=datetime(2026, 7, 10, tzinfo=UTC).date(),
            source="bank_of_russia",
            source_url="https://www.cbr.ru/hd_base/ruonia/dynamics/",
            fetched_at=FETCHED_AT,
            quality_status="actual",
        )

    def get_latest_annual_inflation(self) -> AnnualInflationValue:
        self.inflation_calls += 1
        return AnnualInflationValue(
            value_percent_yoy=Decimal("5.31"),
            period_year=2026,
            period_month=5,
            target_percent=Decimal("4.00"),
            source="rosstat_via_bank_of_russia",
            source_url="https://www.cbr.ru/hd_base/infl/",
            fetched_at=FETCHED_AT,
            quality_status="actual",
        )


class FailingProvider:
    def get_key_rate(self) -> KeyRateValue:
        raise RuntimeError("transport unavailable")

    def get_latest_ruonia(self) -> RuoniaValue:
        raise RuntimeError("transport unavailable")

    def get_latest_annual_inflation(self) -> AnnualInflationValue:
        raise RuntimeError("transport unavailable")
