from datetime import date
from decimal import Decimal

import app.interfaces.cli.commands.cashflow as cashflow_command
import app.interfaces.cli.commands.floaters as floaters_command
import app.interfaces.cli.commands.offers as offers_command
import app.interfaces.cli.commands.portfolio as portfolio_command
import app.interfaces.cli.commands.report as report_command
import app.interfaces.cli.main as cli_main
from app.interfaces.cli.main import main
from app.interfaces.cli.parser import build_parser
from app.domain.portfolio_all import PortfolioAsset
from app.reporting.cashflow import CashflowAccountReport, build_cashflow_report
from app.reporting.offers import OffersAccountReport, build_offers_report
from app.reporting.portfolio import PortfolioAccountReport, build_portfolio_report


def test_parser_exposes_canonical_commands() -> None:
    help_text = build_parser().format_help()

    assert "cashflow" in help_text
    assert "report" in help_text
    assert "portfolio" in help_text
    assert "floaters" in help_text
    assert "offers" in help_text
    assert "demo" in help_text


def test_top_level_legacy_options_delegate_to_legacy_snapshot(monkeypatch) -> None:
    calls = []

    def fake_legacy_main(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(cli_main, "legacy_portfolio_main", fake_legacy_main)

    code = main(["--db-path", "invest.db", "--as-of", "27.04.2026"])

    assert code == 0
    assert calls == [["--db-path", "invest.db", "--as-of", "27.04.2026"]]


def test_cashflow_command_delegates_to_legacy_app_cli(monkeypatch) -> None:
    calls = []
    rendered = []

    def fake_build_report(request):
        calls.append(request)
        return build_cashflow_report(
            as_of=request.as_of,
            months=request.months,
            report_currency=request.report_currency,
            account_results=[CashflowAccountReport(account_label="account_1")],
        )

    def fake_render(report, console):
        rendered.append(report.report_type)

    monkeypatch.setattr(cashflow_command, "build_t_invest_cashflow_report", fake_build_report)
    monkeypatch.setattr(cashflow_command, "render_cashflow_report", fake_render)

    code = main(["cashflow", "--months", "6", "--as-of", "27.04.2026", "--repeat-floating-last-coupon"])

    assert code == 0
    assert calls[0].months == 6
    assert calls[0].as_of == date(2026, 4, 27)
    assert calls[0].report_currency == "RUB"
    assert calls[0].repeat_floating_last_coupon is True
    assert rendered == ["cashflow"]


def test_cashflow_json_format_prints_json(monkeypatch, capsys) -> None:
    def fake_build_report(request):
        return build_cashflow_report(
            as_of=request.as_of,
            months=request.months,
            report_currency=request.report_currency,
            account_results=[CashflowAccountReport(account_label="account_1")],
        )

    monkeypatch.setattr(cashflow_command, "build_t_invest_cashflow_report", fake_build_report)

    code = main(["cashflow", "--months", "1", "--as-of", "27.04.2026", "--format", "json"])

    assert code == 0
    assert '"schema_version": "1.0"' in capsys.readouterr().out


def test_cashflow_csv_format_writes_directory(monkeypatch, tmp_path) -> None:
    def fake_build_report(request):
        return build_cashflow_report(
            as_of=request.as_of,
            months=request.months,
            report_currency=request.report_currency,
            account_results=[CashflowAccountReport(account_label="account_1")],
        )

    monkeypatch.setattr(cashflow_command, "build_t_invest_cashflow_report", fake_build_report)

    code = main(["cashflow", "--months", "1", "--format", "csv", "--output", str(tmp_path)])

    assert code == 0
    assert (tmp_path / "cashflow_monthly.csv").exists()
    assert (tmp_path / "cashflow_events.csv").exists()


def test_demo_cashflow_json_does_not_call_t_invest_builder(monkeypatch, capsys) -> None:
    def fail_if_called(request):
        raise AssertionError("T-Invest builder must not be called for demo")

    monkeypatch.setattr(cashflow_command, "build_t_invest_cashflow_report", fail_if_called)

    code = main(["demo", "cashflow", "--months", "1", "--format", "json"])

    output = capsys.readouterr().out
    assert code == 0
    assert '"account_label": "demo_account"' in output
    assert '"as_of": "2026-07-01"' in output


def test_demo_cashflow_csv_writes_directory(tmp_path) -> None:
    code = main(["demo", "cashflow", "--months", "12", "--format", "csv", "--output", str(tmp_path)])

    assert code == 0
    assert (tmp_path / "cashflow_monthly.csv").exists()
    assert (tmp_path / "cashflow_events.csv").exists()


def test_portfolio_snapshot_command_delegates_to_portfolio_all(monkeypatch) -> None:
    calls = []

    def fake_main(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(portfolio_command.legacy_cli, "main", fake_main)

    code = main(["portfolio", "snapshot", "--account-id", "account-1", "--as-of", "27.04.2026"])

    assert code == 0
    assert calls == [["portfolio-all", "--account-id", "account-1", "--db-path", "invest.db", "--as-of", "27.04.2026"]]


def test_floaters_forecast_command_delegates_to_legacy_name(monkeypatch) -> None:
    calls = []

    def fake_main(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(floaters_command.legacy_cli, "main", fake_main)

    code = main(["floaters", "forecast", "--months", "3", "--scenario", "stress", "--only-unknown", "--as-of", "27.04.2026"])

    assert code == 0
    assert calls == [
        [
            "floating-forecast",
            "--months",
            "3",
            "--scenario",
            "stress",
            "--formulas",
            "app/data/floating_coupon_formulas.yaml",
            "--scenarios",
            "app/data/rate_scenarios.yaml",
            "--only-unknown",
            "--as-of",
            "27.04.2026",
            "--currency",
            "RUB",
        ]
    ]


def test_floaters_scenarios_command_delegates_to_legacy_name(monkeypatch) -> None:
    calls = []

    def fake_main(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(floaters_command.legacy_cli, "main", fake_main)

    code = main(["floaters", "scenarios", "--months", "3", "--delta-percent", "2.5", "--as-of", "27.04.2026"])

    assert code == 0
    assert calls == [["floating-scenarios", "--months", "3", "--delta-percent", "2.5", "--as-of", "27.04.2026"]]


def test_offers_command_delegates_to_legacy_name(monkeypatch) -> None:
    calls = []

    def fake_main(argv):
        calls.append(argv)
        return 0

    monkeypatch.setattr(offers_command.legacy_cli, "main", fake_main)

    code = main(["offers", "--days", "90", "--warning-days", "30", "--as-of", "27.04.2026"])

    assert code == 0
    assert calls == [["offers", "--days", "90", "--warning-days", "30", "--as-of", "27.04.2026"]]


def test_offers_json_format_prints_json(monkeypatch, capsys) -> None:
    def fake_build_report(request):
        return build_offers_report(
            as_of=request.as_of,
            days=request.days,
            warning_days=request.warning_days,
            account_results=[OffersAccountReport(account_label="account_1")],
        )

    monkeypatch.setattr(offers_command, "build_t_invest_offers_report", fake_build_report)

    code = main(["offers", "--days", "90", "--as-of", "27.04.2026", "--format", "json"])

    assert code == 0
    assert '"report_type": "offers"' in capsys.readouterr().out


def test_offers_json_format_writes_output(monkeypatch, tmp_path) -> None:
    def fake_build_report(request):
        return build_offers_report(
            as_of=request.as_of,
            days=request.days,
            warning_days=request.warning_days,
            account_results=[OffersAccountReport(account_label="account_1")],
        )

    monkeypatch.setattr(offers_command, "build_t_invest_offers_report", fake_build_report)

    output = tmp_path / "offers.json"
    code = main(["offers", "--format", "json", "--output", str(output)])

    assert code == 0
    assert '"schema_version": "1.0"' in output.read_text(encoding="utf-8")


def test_report_command_writes_package(monkeypatch, tmp_path) -> None:
    cashflow_calls = []
    offers_calls = []
    portfolio_calls = []

    def fake_cashflow_report(request):
        cashflow_calls.append(request)
        return build_cashflow_report(
            as_of=request.as_of,
            months=request.months,
            report_currency=request.report_currency,
            account_results=[CashflowAccountReport(account_label="account_1")],
            generated_at=request.generated_at,
        )

    def fake_offers_report(request):
        offers_calls.append(request)
        return build_offers_report(
            as_of=request.as_of,
            days=request.days,
            warning_days=request.warning_days,
            account_results=[OffersAccountReport(account_label="account_1")],
            generated_at=request.generated_at,
        )

    def fake_portfolio_report(request):
        portfolio_calls.append(request)
        return build_portfolio_report(
            as_of=request.as_of,
            account_results=[
                PortfolioAccountReport(
                    account_label="account_1",
                    assets=[
                        PortfolioAsset(
                            account_id="account-1",
                            instrument_uid="uid-1",
                            figi="figi-1",
                            ticker="BOND",
                            instrument_type="bond",
                            name="Bond A",
                            isin="RU000A",
                            quantity=Decimal("2"),
                            current_price=Decimal("101.5"),
                            price_currency="RUB",
                        )
                    ],
                )
            ],
            generated_at=request.generated_at,
        )

    monkeypatch.setattr(report_command, "build_t_invest_cashflow_report", fake_cashflow_report)
    monkeypatch.setattr(report_command, "build_t_invest_offers_report", fake_offers_report)
    monkeypatch.setattr(report_command, "build_t_invest_portfolio_report", fake_portfolio_report)

    code = main(["report", "--months", "2", "--as-of", "27.04.2026", "--output", str(tmp_path), "--anonymize"])

    assert code == 0
    assert cashflow_calls[0].months == 2
    assert cashflow_calls[0].include_account_id is False
    assert offers_calls[0].days == 62
    assert portfolio_calls[0].as_of == date(2026, 4, 27)
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "report.html").exists()
    assert "Instrument 1" in (tmp_path / "portfolio.json").read_text(encoding="utf-8")


def test_demo_report_does_not_call_t_invest_builders(monkeypatch, tmp_path) -> None:
    def fail_cashflow(request):
        raise AssertionError("T-Invest cashflow builder must not be called for demo report")

    def fail_offers(request):
        raise AssertionError("T-Invest offers builder must not be called for demo report")

    def fail_portfolio(request):
        raise AssertionError("T-Invest portfolio builder must not be called for demo report")

    monkeypatch.setattr(report_command, "build_t_invest_cashflow_report", fail_cashflow)
    monkeypatch.setattr(report_command, "build_t_invest_offers_report", fail_offers)
    monkeypatch.setattr(report_command, "build_t_invest_portfolio_report", fail_portfolio)

    code = main(["demo", "report", "--months", "12", "--output", str(tmp_path)])

    assert code == 0
    assert (tmp_path / "manifest.json").exists()
    assert '"mode": "demo"' in (tmp_path / "manifest.json").read_text(encoding="utf-8")


def test_parser_converts_dates() -> None:
    args = build_parser().parse_args(["cashflow", "--as-of", "27.04.2026"])

    assert args.as_of == date(2026, 4, 27)
