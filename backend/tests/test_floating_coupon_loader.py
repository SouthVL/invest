from decimal import Decimal

from app.config.floating_coupon_loader import load_floating_coupon_formulas, load_rate_scenario
from app.domain.floating_coupon import FormulaDataQuality, FloatingRateIndex, VersionedStatus


def test_load_rate_scenario_reads_versioned_metadata(tmp_path) -> None:
    path = tmp_path / "scenarios.yaml"
    path.write_text(
        """
scenarios:
  base:
    id: cb-key-rate-base-2026-07
    name: Base key-rate scenario
    description: Gradual easing
    status: active
    created_at: 2026-07-06
    updated_at: 2026-07-07
    author: Cooperative South
    source:
      title: Manual editorial scenario
      url: null
    market: RU
    currency: RUB
    time_range: 2026-07..2026-09
    assumptions:
      - Gradual easing
    rates:
      key_rate:
        2026-07: 18.0
        2026-08: 17.5
""",
        encoding="utf-8",
    )

    scenario = load_rate_scenario(path, "base")

    assert scenario.id == "cb-key-rate-base-2026-07"
    assert scenario.name == "Base key-rate scenario"
    assert scenario.status == VersionedStatus.ACTIVE
    assert scenario.created_at.isoformat() == "2026-07-06"
    assert scenario.source is not None
    assert scenario.source.title == "Manual editorial scenario"
    assert scenario.market == "RU"
    assert scenario.currency == "RUB"
    assert scenario.assumptions == ["Gradual easing"]
    assert scenario.index == FloatingRateIndex.KEY_RATE
    assert scenario.monthly_rates["2026-07"] == Decimal("18.0")


def test_load_rate_scenario_keeps_legacy_format_compatible(tmp_path) -> None:
    path = tmp_path / "legacy-scenarios.yaml"
    path.write_text(
        """
scenarios:
  base:
    key_rate:
      2026-07: 18.0
""",
        encoding="utf-8",
    )

    scenario = load_rate_scenario(path, "base")

    assert scenario.id == "base"
    assert scenario.name == "base"
    assert scenario.status == VersionedStatus.ACTIVE
    assert scenario.monthly_rates == {"2026-07": Decimal("18.0")}


def test_load_floating_coupon_formulas_reads_versioned_metadata(tmp_path) -> None:
    path = tmp_path / "formulas.yaml"
    path.write_text(
        """
formulas:
  RU000A:
    isin: RU000A
    name: Known floater
    base_index: key_rate
    spread_bps: 130
    day_count: ACT/365
    coupon_period_days: 91
    lag_days: 7
    source:
      title: Issuer decision
      url: https://example.test/formula
    verified_at: 2026-07-06
    comment: Checked manually
    status: active
    data_quality_status: verified
    confidence: high
""",
        encoding="utf-8",
    )

    formula = load_floating_coupon_formulas(path)["RU000A"]

    assert formula.name == "Known floater"
    assert formula.index == FloatingRateIndex.KEY_RATE
    assert formula.base_index == FloatingRateIndex.KEY_RATE
    assert formula.day_count == "ACT/365"
    assert formula.lag_days == 7
    assert formula.source.title == "Issuer decision"
    assert formula.verified_at.isoformat() == "2026-07-06"
    assert formula.status == VersionedStatus.ACTIVE
    assert formula.data_quality_status == FormulaDataQuality.VERIFIED


def test_load_floating_coupon_formulas_keeps_legacy_format_compatible(tmp_path) -> None:
    path = tmp_path / "legacy-formulas.yaml"
    path.write_text(
        """
RU000A:
  index: key_rate
  spread_bps: 130
  coupon_period_days: 91
""",
        encoding="utf-8",
    )

    formula = load_floating_coupon_formulas(path)["RU000A"]

    assert formula.isin == "RU000A"
    assert formula.index == FloatingRateIndex.KEY_RATE
    assert formula.status == VersionedStatus.ACTIVE
    assert formula.data_quality_status == FormulaDataQuality.MANUAL
