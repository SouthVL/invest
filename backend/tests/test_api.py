from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.api.session_store import SESSION_COOKIE_NAME, clear_sessions, create_session
from app.domain.cashflow import CashflowEvent, CashflowSource, CashflowType
from app.domain.portfolio_all import PortfolioAsset, PortfolioSnapshot
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


def test_income_endpoint_returns_income_only_contract_and_filters(monkeypatch) -> None:
    clear_sessions()

    class StubAdapter:
        def __init__(self, token: str) -> None:
            self.token = token

        def get_accounts(self) -> list[AccountSummary]:
            return [
                AccountSummary(id="100000000001", name="First"),
            ]

    class StubClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def __enter__(self) -> "StubClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class StubIncomeService:
        def __init__(self, client: StubClient) -> None:
            self.client = client

        def get_portfolio_cashflow_events(self, **kwargs) -> list[CashflowEvent]:
            from_date = kwargs["from_date"]
            return [
                CashflowEvent(
                    instrument_uid="coupon-uid",
                    name="Coupon Bond",
                    event_date=from_date + timedelta(days=10),
                    event_type=CashflowType.COUPON,
                    amount_per_bond=Decimal("10.00"),
                    quantity=Decimal("10"),
                    total_amount=Decimal("100.00"),
                    source=CashflowSource.ACTUAL,
                ),
                CashflowEvent(
                    instrument_uid="floating-uid",
                    name="Floating Bond",
                    event_date=from_date + timedelta(days=20),
                    event_type=CashflowType.COUPON,
                    amount_per_bond=Decimal("5.00"),
                    quantity=Decimal("5"),
                    total_amount=Decimal("25.00"),
                    source=CashflowSource.REPEATED_FLOATING_COUPON,
                ),
                CashflowEvent(
                    instrument_uid="share-uid",
                    name="Dividend Share",
                    event_date=from_date + timedelta(days=30),
                    event_type=CashflowType.DIVIDEND,
                    amount_per_bond=Decimal("2.50"),
                    quantity=Decimal("20"),
                    total_amount=Decimal("50.00"),
                    source=CashflowSource.ACTUAL,
                ),
                CashflowEvent(
                    instrument_uid="maturity-uid",
                    name="Maturity Bond",
                    event_date=from_date + timedelta(days=40),
                    event_type=CashflowType.MATURITY,
                    amount_per_bond=Decimal("1000.00"),
                    quantity=Decimal("1"),
                    total_amount=Decimal("1000.00"),
                    source=CashflowSource.ACTUAL,
                ),
            ]

    monkeypatch.setattr("app.api.routes.session.TInvestAdapter", StubAdapter)
    monkeypatch.setattr("app.api.routes.income.configure_t_invest_sdk", lambda: None)
    monkeypatch.setattr("app.api.routes.income.TInvestCashflowService", StubIncomeService)
    monkeypatch.setattr("t_tech.invest.Client", StubClient)
    client = TestClient(create_app())

    connect_response = client.post("/api/v1/session/connect", json={"token": "test-read-only-token"})
    assert connect_response.status_code == 200

    response = client.get("/api/v1/income", params={"period": "3m", "type": "all", "status": "all"})

    assert response.status_code == 200
    assert "test-read-only-token" not in response.text
    assert "100000000001" not in response.text
    payload = response.json()
    assert payload["report_type"] == "income"
    assert payload["period"]["label"] == "3m"
    assert payload["period"]["from"]
    assert payload["period"]["to"]
    assert payload["generated_at"].endswith("Z")
    assert payload["summary"]["total"] == {"amount": "175.00", "currency": "RUB"}
    assert payload["summary"]["coupons"] == {"amount": "125.00", "currency": "RUB"}
    assert payload["summary"]["dividends"] == {"amount": "50.00", "currency": "RUB"}
    assert payload["summary"]["confirmed"] == {"amount": "150.00", "currency": "RUB"}
    assert payload["summary"]["forecast"] == {"amount": "25.00", "currency": "RUB"}
    assert {payment["income_type"] for payment in payload["payments"]} == {"coupon", "dividend"}
    assert "maturity" not in response.text

    dividend_response = client.get("/api/v1/income", params={"type": "dividend", "status": "confirmed"})
    assert dividend_response.status_code == 200
    dividend_payload = dividend_response.json()
    assert dividend_payload["summary"]["total"] == {"amount": "50.00", "currency": "RUB"}
    assert [payment["income_type"] for payment in dividend_payload["payments"]] == ["dividend"]


def test_income_endpoint_requires_connected_session() -> None:
    clear_sessions()
    client = TestClient(create_app())

    response = client.get("/api/v1/income")

    assert response.status_code == 401


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


def test_session_status_returns_active_session_without_token_or_account_ids(monkeypatch) -> None:
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

    response = client.get("/api/v1/session/status")

    assert response.status_code == 200
    assert "test-read-only-token" not in response.text
    assert "100000000001" not in response.text
    assert "100000000002" not in response.text
    payload = response.json()
    assert payload["session"]["status"] == "connected"
    assert payload["session"]["expires_at"].endswith("Z")
    assert payload["session"]["selected_account"] == {
        "ref": "portfolio_all",
        "name": "Весь портфель",
    }
    assert payload["accounts"][0] == {
        "ref": "portfolio_all",
        "name": "Весь портфель",
        "type": "aggregate",
        "status": "mixed",
        "masked_id": "2 счета",
        "selected": True,
    }


def test_session_status_returns_missing_without_cookie() -> None:
    clear_sessions()
    client = TestClient(create_app())

    response = client.get("/api/v1/session/status")

    assert response.status_code == 200
    assert response.json() == {
        "session": {
            "status": "missing",
            "expires_at": None,
            "selected_account": None,
        },
        "accounts": [],
    }


def test_session_status_returns_expired_without_leaking_session_data() -> None:
    clear_sessions()
    record = create_session(
        token="test-read-only-token",
        accounts=[
            AccountSummary(id="100000000001", name="First"),
        ],
    )
    record.expires_at = datetime(2000, 1, 1, tzinfo=UTC)
    client = TestClient(create_app())
    client.cookies.set(SESSION_COOKIE_NAME, record.session_id)

    response = client.get("/api/v1/session/status")

    assert response.status_code == 200
    assert response.json() == {
        "session": {
            "status": "expired",
            "expires_at": None,
            "selected_account": None,
        },
        "accounts": [],
    }
    assert "test-read-only-token" not in response.text
    assert "100000000001" not in response.text


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


def test_real_positions_endpoint_returns_all_positions_without_leaking_session_data(monkeypatch) -> None:
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
        def __init__(self, client: StubClient) -> None:
            self.client = client

        def get_portfolio_snapshot(self, account_id: str, as_of: date) -> PortfolioSnapshot:
            account_index = "first" if account_id.endswith("1") else "second"
            assets = [
                PortfolioAsset(
                    account_id=account_id,
                    instrument_uid=f"uid-{account_index}-bond",
                    ticker="BOND",
                    instrument_type="bond",
                    name="Bond",
                    isin="RU000BOND",
                    quantity=Decimal("2"),
                    average_position_price=Decimal("100.00"),
                    current_price=Decimal("105.00"),
                    price_currency="RUB",
                )
            ]
            if account_id.endswith("2"):
                assets.append(
                    PortfolioAsset(
                        account_id=account_id,
                        instrument_uid="uid-second-share",
                        ticker="SHARE",
                        instrument_type="share",
                        name="Share",
                        isin="RU000SHARE",
                        quantity=Decimal("3"),
                        average_position_price=Decimal("10.00"),
                        current_price=None,
                        price_currency="RUB",
                    )
                )
            return PortfolioSnapshot(
                account_id=account_id,
                fetched_at=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
                as_of=as_of,
                assets=assets,
                total_value=Decimal("210.00"),
                total_value_currency="RUB",
            )

    monkeypatch.setattr("app.api.routes.session.TInvestAdapter", StubAdapter)
    monkeypatch.setattr("app.api.routes.portfolio.configure_t_invest_sdk", lambda: None)
    monkeypatch.setattr("app.api.routes.portfolio.TInvestPortfolioAllService", StubPortfolioService)
    monkeypatch.setattr("t_tech.invest.Client", StubClient)
    client = TestClient(create_app())

    connect_response = client.post("/api/v1/session/connect", json={"token": "test-read-only-token"})
    assert connect_response.status_code == 200

    response = client.get("/api/v1/portfolio/positions")

    assert response.status_code == 200
    assert "test-read-only-token" not in response.text
    assert "100000000001" not in response.text
    assert "100000000002" not in response.text
    payload = response.json()
    assert payload["report_type"] == "portfolio_positions"
    assert payload["account_label"] == "Весь портфель"
    assert len(payload["positions"]) == 3
    assert {position["instrument_type"] for position in payload["positions"]} == {"bond", "share"}
    assert any(position["current_price"] is None and position["market_value"] is None for position in payload["positions"])


def test_real_dashboard_aggregate_account_returns_partial_data_when_one_account_fails(monkeypatch) -> None:
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
            if account_id == "100000000002":
                raise RuntimeError("upstream failure for 100000000002")
            return PortfolioSnapshot(
                account_id=account_id,
                fetched_at=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
                as_of=as_of,
                assets=[],
                total_value=Decimal("100.00"),
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
    assert "test-read-only-token" not in dashboard_response.text
    assert "100000000001" not in dashboard_response.text
    assert "100000000002" not in dashboard_response.text
    payload = dashboard_response.json()
    assert payload["portfolio"]["account_label"] == "Весь портфель"
    assert payload["portfolio"]["total_value"] == {"amount": "100.00", "currency": "RUB"}
    assert payload["warnings"] == ["Could not load portfolio data for account_2."]


def test_real_dashboard_aggregate_account_returns_safe_error_when_all_accounts_fail(monkeypatch) -> None:
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
        def __init__(self, client: StubClient) -> None:
            self.client = client

        def get_portfolio_snapshot(self, account_id: str, as_of: date) -> PortfolioSnapshot:
            raise RuntimeError(f"upstream failure for {account_id}")

    monkeypatch.setattr("app.api.routes.session.TInvestAdapter", StubAdapter)
    monkeypatch.setattr("app.api.routes.portfolio.configure_t_invest_sdk", lambda: None)
    monkeypatch.setattr("app.api.routes.portfolio.TInvestPortfolioAllService", StubPortfolioService)
    monkeypatch.setattr("t_tech.invest.Client", StubClient)
    client = TestClient(create_app())

    connect_response = client.post("/api/v1/session/connect", json={"token": "test-read-only-token"})
    assert connect_response.status_code == 200

    dashboard_response = client.get("/api/v1/portfolio/dashboard")

    assert dashboard_response.status_code == 502
    assert dashboard_response.json() == {"detail": "Portfolio data is unavailable for all selected accounts."}
    assert "test-read-only-token" not in dashboard_response.text
    assert "100000000001" not in dashboard_response.text
    assert "100000000002" not in dashboard_response.text


def test_real_dashboard_requires_connected_session() -> None:
    clear_sessions()
    client = TestClient(create_app())

    response = client.get("/api/v1/portfolio/dashboard")

    assert response.status_code == 401
