from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Cookie, HTTPException, Query, status

from app.analytics.cashflow_forecast import _add_months, build_monthly_cashflow
from app.api.services.income import build_income_response
from app.api.session_store import SESSION_COOKIE_NAME, get_session, selected_account, selected_accounts
from app.reporting.cashflow import CashflowAccountReport, build_cashflow_report
from app.t_invest.cashflow import TInvestCashflowService
from invest_bonds.sdk_compat import configure_t_invest_sdk

router = APIRouter()

Period = Literal["3m", "6m", "12m"]
IncomeType = Literal["all", "coupon", "dividend"]
IncomeStatus = Literal["all", "confirmed", "forecast"]


@router.get("/income")
def income(
    period: Period = Query(default="3m"),
    income_type: IncomeType = Query(default="all", alias="type"),
    income_status: IncomeStatus = Query(default="all", alias="status"),
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, object]:
    record = get_session(session_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is not connected.")

    account = selected_account(record)
    if account is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No account is selected.")
    accounts = selected_accounts(record)
    if not accounts:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No account is selected.")

    configure_t_invest_sdk()
    from t_tech.invest import Client

    months = period_months(period)
    as_of = date.today()
    to_date = _add_months(as_of, months)
    with Client(record.token) as client:
        service = TInvestCashflowService(client)
        account_results = []
        warnings = []
        for session_account in accounts:
            try:
                events = service.get_portfolio_cashflow_events(
                    account_id=session_account.account_ids[0],
                    from_date=as_of,
                    to_date=to_date,
                    repeat_floating_last_coupon=True,
                    report_currency="RUB",
                )
            except Exception:
                warnings.append(f"Could not load income data for {session_account.ref}.")
                continue
            account_results.append(
                CashflowAccountReport(
                    account_label=session_account.name or session_account.ref,
                    monthly=build_monthly_cashflow(events, start_date=as_of, months=months, currency="RUB"),
                    events=events,
                )
            )

    if not account_results:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Income data is unavailable for all selected accounts.")

    report = build_cashflow_report(as_of=as_of, months=months, report_currency="RUB", account_results=account_results)
    report = report.model_copy(update={"warnings": [*report.warnings, *warnings]})
    return build_income_response(report=report, period_label=period, income_type=income_type, status=income_status)


def period_months(period: Period) -> int:
    return {"3m": 3, "6m": 6, "12m": 12}[period]
