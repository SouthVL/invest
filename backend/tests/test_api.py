from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.api.session_store import clear_sessions
from app.domain.portfolio_all import PortfolioSnapshot
from invest_bonds.models import AccountSummary


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "south-invest-api"
    assert payload["updated_at"].endswith("Z")


def test_demo_dashboard_endpoint_is_read_only_and_deterministic() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/demo/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "demo"
    assert payload["portfolio"]["total_value"] == {"amount": "17615.00", "currency": "RUB"}
    assert payload["portfolio"]["period"] == "2026-07-01"
    assert payload["macro"]["status"] == "unavailable"
    assert payload["macro"]["key_rate"] is None
    assert payload["positions_preview"]


def test_demo_cashflow_endpoint_uses_months_query() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/demo/cashflow", params={"months": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["report_type"] == "cashflow"
    assert payload["months"] == 1
    assert payload["summary"]["total"] == {"amount": "350.00", "currency": "RUB"}


def test_demo_cashflow_endpoint_validates_months() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/demo/cashflow", params={"months": 0})

    assert response.status_code == 422


def test_session_connect_sets_http_only_cookie_without_leaking_token_or_account_id(monkeypatch) -> None:
    clear_sessions()

    class StubAdapter:
        def __init__(self, token: str) -> None:
            self.token = token

        def get_accounts(self) -> list[AccountSummary]:
            assert self.token == "test-read-only-token"
            return [
                AccountSummary(
                    id="200012345678",
                    name="Main account",
                    type="ACCOUNT_TYPE_TINKOFF",
                    status="ACCOUNT_STATUS_OPEN",
                )
            ]

    monkeypatch.setattr("app.api.routes.session.TInvestAdapter", StubAdapter)
    client = TestClient(create_app())

    response = client.post("/api/v1/session/connect", json={"token": "test-read-only-token"})

    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    response_text = response.text
    assert "test-read-only-token" not in response_text
    assert "200012345678" not in response_text
    payload = response.json()
    assert payload["session"]["status"] == "connected"
    assert payload["accounts"] == [
        {
            "ref": "account_1",
            "name": "Main account",
            "type": "ACCOUNT_TYPE_TINKOFF",
            "status": "ACCOUNT_STATUS_OPEN",
            "masked_id": "****5678",
            "selected": True,
        }
    ]


def test_session_account_selection_uses_public_account_refs(monkeypatch) -> None:
    clear_sessions()

    class StubAdapter:
        def __init__(self, token: str) -> None:
            self.token = token

        def get_accounts(self) -> list[AccountSummary]:
            return [
                AccountSummary(id="100000000001", name="First"),
                AccountSummary(id="100000000002", name="Second"),
            ]

    monkeypatch.setattr("app.api.routes.session.TInvestAdapter", StubAdapter)
    client = TestClient(create_app())

    connect_response = client.post("/api/v1/session/connect", json={"token": "test-read-only-token"})
    assert connect_response.status_code == 200

    select_response = client.post("/api/v1/accounts/select", json={"account_ref": "account_2"})

    assert select_response.status_code == 200
    accounts = select_response.json()["accounts"]
    assert accounts[0] == {
        "ref": "portfolio_all",
        "name": "Весь портфель",
        "type": "aggregate",
        "status": "mixed",
        "masked_id": "2 счета",
        "selected": False,
    }
    assert [account["selected"] for account in accounts] == [False, False, True]
    assert "100000000002" not in select_response.text


def test_session_connect_adds_aggregate_portfolio_account_for_multiple_accounts(monkeypatch) -> None:
    clear_sessions()

    class StubAdapter:
        def __init__(self, token: str) -> None:
            self.token = token

        def get_accounts(self) -> list[AccountSummary]:
            return [
                AccountSummary(id="100000000001", name="First"),
                AccountSummary(id="100000000002", name="Second"),
            ]

    monkeypatch.setattr("app.api.routes.session.TInvestAdapter", StubAdapter)
    client = TestClient(create_app())

    response = client.post("/api/v1/session/connect", json={"token": "test-read-only-token"})

    assert response.status_code == 200
    accounts = response.json()["accounts"]
    assert accounts[0] == {
        "ref": "portfolio_all",
        "name": "Весь портфель",
        "type": "aggregate",
        "status": "mixed",
        "masked_id": "2 счета",
        "selected": True,
    }
    assert [account["ref"] for account in accounts] == ["portfolio_all", "account_1", "account_2"]
    assert "100000000001" not in response.text
    assert "100000000002" not in response.text


def test_real_dashboard_aggregate_account_fetches_all_account_snapshots(monkeypatch) -> None:
    clear_sessions()

    class StubAdapter:
        def __init__(self, token: str) -> None:
            self.token = token

        def get_accounts(self) -> list[AccountSummary]:
            return [
                AccountSummary(id="100000000001", name="First"),
                AccountSummary(id="100000000002", name="Second"),
            ]

    class StubClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def __enter__(self) -> "StubClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class StubPortfolioService:
        seen_account_ids: list[str] = []

        def __init__(self, client: StubClient) -> None:
            self.client = client

        def get_portfolio_snapshot(self, account_id: str, as_of: date) -> PortfolioSnapshot:
            self.seen_account_ids.append(account_id)
            return PortfolioSnapshot(
                account_id=account_id,
                fetched_at=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
                as_of=as_of,
                assets=[],
                total_value=Decimal("100.00") if account_id.endswith("1") else Decimal("250.00"),
                total_value_currency="RUB",
            )

    monkeypatch.setattr("app.api.routes.session.TInvestAdapter", StubAdapter)
    monkeypatch.setattr("app.api.routes.portfolio.configure_t_invest_sdk", lambda: None)
    monkeypatch.setattr("app.api.routes.portfolio.TInvestPortfolioAllService", StubPortfolioService)
    monkeypatch.setattr("t_tech.invest.Client", StubClient)
    client = TestClient(create_app())

    connect_response = client.post("/api/v1/session/connect", json={"token": "test-read-only-token"})
    assert connect_response.status_code == 200

    dashboard_response = client.get("/api/v1/portfolio/dashboard")

    assert dashboard_response.status_code == 200
    assert StubPortfolioService.seen_account_ids == ["100000000001", "100000000002"]
    payload = dashboard_response.json()
    assert payload["portfolio"]["account_label"] == "Весь портфель"
    assert payload["portfolio"]["total_value"] == {"amount": "350.00", "currency": "RUB"}


def test_real_dashboard_requires_connected_session() -> None:
    clear_sessions()
    client = TestClient(create_app())

    response = client.get("/api/v1/portfolio/dashboard")

    assert response.status_code == 401
