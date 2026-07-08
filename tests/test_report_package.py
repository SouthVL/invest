import json

from app.demo.provider import build_demo_cashflow_report, build_demo_offers_report, build_demo_portfolio_report
from app.reporting.report_package import write_report_package


def test_report_package_writes_expected_files(tmp_path) -> None:
    package = write_report_package(
        output_dir=tmp_path,
        cashflow_report=build_demo_cashflow_report(months=12),
        offers_report=build_demo_offers_report(days=180),
        portfolio_report=build_demo_portfolio_report(),
        mode="demo",
    )

    expected_files = {
        "manifest.json",
        "summary.json",
        "portfolio.json",
        "portfolio.csv",
        "cashflow_monthly.json",
        "cashflow_monthly.csv",
        "cashflow_events.json",
        "cashflow_events.csv",
        "maturities.csv",
        "offers.json",
        "offers.csv",
        "floating_scenarios.json",
        "floating_scenarios.csv",
        "data_quality.json",
        "report.html",
        "charts/cashflow_monthly.svg",
        "charts/cashflow_cumulative.svg",
        "charts/payment_structure.svg",
        "charts/offers_timeline.svg",
        "charts/floating_scenarios.svg",
    }

    assert {path.relative_to(tmp_path).as_posix() for path in package.files} == expected_files
    assert (tmp_path / "report.html").read_text(encoding="utf-8").startswith("<!doctype html>")


def test_report_package_manifest_and_summary_are_stable(tmp_path) -> None:
    write_report_package(
        output_dir=tmp_path,
        cashflow_report=build_demo_cashflow_report(months=12),
        offers_report=build_demo_offers_report(days=180),
        portfolio_report=build_demo_portfolio_report(),
        mode="demo",
    )

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    portfolio = json.loads((tmp_path / "portfolio.json").read_text(encoding="utf-8"))

    assert manifest["report_id"] == "2026-07-01-demo-001"
    assert manifest["mode"] == "demo"
    assert manifest["files"][0] == {"path": "summary.json", "type": "summary", "format": "json"}
    assert summary["expected_cashflow"] == {"amount": "6251.00", "currency": "RUB"}
    assert summary["forecast_share"] == "0.0688"
    assert summary["average_monthly_cashflow"] == {"amount": "520.92", "currency": "RUB"}
    assert summary["currency_structure"] == [
        {"currency": "RUB", "amount": "5801.00"},
        {"currency": "USD", "amount": "5.00"},
    ]
    assert portfolio["report_type"] == "portfolio"
    assert portfolio["summary"]["asset_count"] == 3
    assert portfolio["summary"]["market_value_by_currency"] == [{"currency": "RUB", "amount": "17615.00"}]
    assert portfolio["accounts"][0]["assets"][0]["instrument_name"] == "Demo Government Fixed Bond"
    assert "Portfolio holdings snapshot is not included" not in (tmp_path / "portfolio.csv").read_text(encoding="utf-8")


def test_report_package_floating_scenarios_include_statuses_and_csv_rows(tmp_path) -> None:
    write_report_package(
        output_dir=tmp_path,
        cashflow_report=build_demo_cashflow_report(months=12),
        offers_report=build_demo_offers_report(days=180),
        portfolio_report=build_demo_portfolio_report(),
        mode="demo",
        scenario="base",
    )

    payload = json.loads((tmp_path / "floating_scenarios.json").read_text(encoding="utf-8"))
    csv_text = (tmp_path / "floating_scenarios.csv").read_text(encoding="utf-8")
    svg_text = (tmp_path / "charts" / "floating_scenarios.svg").read_text(encoding="utf-8")

    assert payload["report_type"] == "floating_scenarios"
    assert payload["scenario"] == "base"
    assert payload["events"] == [
        {
            "instrument_name": "Demo Key Rate Floater",
            "payment_date": "2026-09-15",
            "scenario": "base",
            "amount": {"amount": "421.00", "currency": "RUB"},
            "source": "floating",
            "source_status": "actual",
        },
        {
            "instrument_name": "Demo Key Rate Floater",
            "payment_date": "2026-12-15",
            "scenario": "base",
            "amount": {"amount": "430.00", "currency": "RUB"},
            "source": "floating: last coupon",
            "source_status": "estimated",
        },
    ]
    assert csv_text.splitlines()[0] == "instrument_name,payment_date,scenario,total_amount,currency,source,source_status"
    assert "Demo Key Rate Floater,2026-09-15,base,421.00,RUB,floating,actual" in csv_text
    assert "Demo Key Rate Floater,2026-12-15,base,430.00,RUB,floating: last coupon,estimated" in csv_text
    assert "actual" in svg_text
    assert "estimated" in svg_text


def test_report_package_anonymize_hides_identifiers(tmp_path) -> None:
    write_report_package(
        output_dir=tmp_path,
        cashflow_report=build_demo_cashflow_report(months=12),
        offers_report=build_demo_offers_report(days=180),
        portfolio_report=build_demo_portfolio_report(),
        mode="demo",
        anonymize=True,
    )

    events = (tmp_path / "cashflow_events.json").read_text(encoding="utf-8")
    offers = (tmp_path / "offers.json").read_text(encoding="utf-8")
    portfolio = (tmp_path / "portfolio.json").read_text(encoding="utf-8")
    data_quality = json.loads((tmp_path / "data_quality.json").read_text(encoding="utf-8"))

    assert "DEMOFIGI" not in events
    assert "DEMO000" not in events
    assert "Demo Government Fixed Bond" not in events
    assert "Instrument 1" in events
    assert "DEMOFIGI" not in offers
    assert "DEMOFIGI" not in portfolio
    assert "Demo Government Fixed Bond" not in portfolio
    assert "Instrument 1" in portfolio
    assert data_quality["anonymized"] is True
    assert data_quality["portfolio"]["asset_count"] == 3


def test_report_html_has_no_external_scripts_or_fonts(tmp_path) -> None:
    write_report_package(
        output_dir=tmp_path,
        cashflow_report=build_demo_cashflow_report(months=12),
        offers_report=build_demo_offers_report(days=180),
        portfolio_report=build_demo_portfolio_report(),
        mode="demo",
    )

    html = (tmp_path / "report.html").read_text(encoding="utf-8")

    assert "<script" not in html
    assert "https://" not in html
    assert "@import" not in html
