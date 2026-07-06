from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from app.domain.floating_coupon import FloatingCouponFormula, FloatingRateIndex, RateScenario


def load_floating_coupon_formulas(path: str | Path) -> dict[str, FloatingCouponFormula]:
    with Path(path).open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}
    return {
        isin: FloatingCouponFormula(isin=isin, **(payload or {}))
        for isin, payload in raw.items()
    }


def load_rate_scenario(path: str | Path, scenario_name: str, index: FloatingRateIndex = FloatingRateIndex.KEY_RATE) -> RateScenario:
    with Path(path).open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    scenarios = raw.get("scenarios", {})
    if scenario_name not in scenarios:
        available = ", ".join(sorted(scenarios)) or "none"
        raise ValueError(f"Unknown scenario '{scenario_name}'. Available: {available}")

    scenario_payload = scenarios[scenario_name] or {}
    rates_payload = scenario_payload.get(index.value)
    selected_index = index
    if rates_payload is None:
        selected_index, rates_payload = _first_available_index(scenario_payload)

    rates = {month: _decimal(value) for month, value in (rates_payload or {}).items()}
    return RateScenario(name=scenario_name, index=selected_index, monthly_rates=rates)


def _first_available_index(payload: dict[str, Any]) -> tuple[FloatingRateIndex, dict[str, Any]]:
    for index in FloatingRateIndex:
        if index == FloatingRateIndex.UNKNOWN:
            continue
        if index.value in payload:
            return index, payload[index.value] or {}
    return FloatingRateIndex.UNKNOWN, {}


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))
