from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import create_app


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
