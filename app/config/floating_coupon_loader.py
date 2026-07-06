from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from app.domain.floating_coupon import DataSource, FloatingCouponFormula, FloatingRateIndex, RateScenario


def load_floating_coupon_formulas(path: str | Path) -> dict[str, FloatingCouponFormula]:
    with Path(path).open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    formulas_payload = raw.get("formulas", raw)
    if isinstance(formulas_payload, list):
        formulas = [formula_from_payload(payload) for payload in formulas_payload]
    else:
        formulas = [formula_from_payload({"isin": isin, **(payload or {})}) for isin, payload in formulas_payload.items()]
    return {formula.isin: formula for formula in formulas}


def load_rate_scenario(path: str | Path, scenario_name: str, index: FloatingRateIndex = FloatingRateIndex.KEY_RATE) -> RateScenario:
    with Path(path).open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    scenarios = raw.get("scenarios", {})
    scenario_key, scenario_payload = find_scenario_payload(scenarios, scenario_name)
    if scenario_payload is None:
        available = ", ".join(sorted(scenarios)) or "none"
        raise ValueError(f"Unknown scenario '{scenario_name}'. Available: {available}")

    scenario_payload = scenario_payload or {}
    rates_container = scenario_payload.get("rates", scenario_payload)
    rates_payload = rates_container.get(index.value) if isinstance(rates_container, dict) else None
    selected_index = index
    if rates_payload is None:
        selected_index, rates_payload = _first_available_index(rates_container if isinstance(rates_container, dict) else {})

    rates = {month: _decimal(value) for month, value in (rates_payload or {}).items()}
    source = scenario_payload.get("source")
    return RateScenario(
        id=scenario_payload.get("id") or scenario_key,
        name=scenario_payload.get("name") or scenario_key,
        description=scenario_payload.get("description"),
        status=scenario_payload.get("status", "active"),
        created_at=scenario_payload.get("created_at"),
        updated_at=scenario_payload.get("updated_at"),
        author=scenario_payload.get("author"),
        source=DataSource(**source) if isinstance(source, dict) else None,
        currency=scenario_payload.get("currency"),
        market=scenario_payload.get("market"),
        time_range=scenario_payload.get("time_range"),
        assumptions=scenario_payload.get("assumptions") or [],
        index=selected_index,
        monthly_rates=rates,
    )


def formula_from_payload(payload: dict[str, Any]) -> FloatingCouponFormula:
    payload = dict(payload or {})
    if "isin" not in payload:
        raise ValueError("Floating coupon formula must include ISIN")
    if "base_index" in payload and "index" not in payload:
        payload["index"] = payload["base_index"]
    source = payload.get("source")
    if isinstance(source, dict):
        payload["source"] = DataSource(**source)
    return FloatingCouponFormula(**payload)


def find_scenario_payload(scenarios: dict[str, Any], scenario_name: str) -> tuple[str, dict[str, Any] | None]:
    if scenario_name in scenarios:
        return scenario_name, scenarios[scenario_name]
    for key, payload in scenarios.items():
        if isinstance(payload, dict) and payload.get("id") == scenario_name:
            return key, payload
    return scenario_name, None


def _first_available_index(payload: dict[str, Any]) -> tuple[FloatingRateIndex, dict[str, Any]]:
    for index in FloatingRateIndex:
        if index == FloatingRateIndex.UNKNOWN:
            continue
        if index.value in payload:
            return index, payload[index.value] or {}
    return FloatingRateIndex.UNKNOWN, {}


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))
