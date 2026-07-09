from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.services.demo_dashboard import build_demo_dashboard
from app.demo.provider import build_demo_cashflow_report
from app.reporting.serializers.cashflow_json import cashflow_report_to_dict

router = APIRouter()


@router.get("/dashboard")
def demo_dashboard() -> dict[str, object]:
    return build_demo_dashboard()


@router.get("/cashflow")
def demo_cashflow(months: int = Query(default=12, ge=1, le=120)) -> dict[str, object]:
    return cashflow_report_to_dict(build_demo_cashflow_report(months=months))
