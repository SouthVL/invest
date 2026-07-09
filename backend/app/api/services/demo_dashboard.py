from __future__ import annotations

from typing import Any

from app.api.services.dashboard import build_dashboard
from app.demo.provider import build_demo_cashflow_report, build_demo_portfolio_report
from app.reporting.serializers.cashflow_json import iso_datetime, money


def build_demo_dashboard() -> dict[str, Any]:
    portfolio = build_demo_portfolio_report()
    cashflow = build_demo_cashflow_report(months=12)
    cashflow_summary = {
        "period": {
            "as_of": cashflow.as_of.isoformat(),
            "months": cashflow.months,
        },
        "updated_at": iso_datetime(cashflow.generated_at),
        "total": money(cashflow.summary.total, cashflow.summary.currency),
        "actual_total": money(cashflow.summary.actual_total, cashflow.summary.currency),
        "estimated_total": money(cashflow.summary.estimated_total, cashflow.summary.currency),
        "unknown_count": cashflow.summary.unknown_count,
    }
    dashboard = build_dashboard(
        portfolio=portfolio,
        mode="demo",
        account_label="demo_account",
        cashflow_summary=cashflow_summary,
    )
    dashboard["warnings"] = cashflow.warnings + dashboard["warnings"]
    return dashboard
