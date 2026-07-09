from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, status

from app.api.services.dashboard import build_dashboard
from app.api.session_store import SESSION_COOKIE_NAME, get_session, selected_account
from app.reporting.portfolio import PortfolioAccountReport, build_portfolio_report
from app.t_invest.portfolio_all import TInvestPortfolioAllService
from invest_bonds.sdk_compat import configure_t_invest_sdk

router = APIRouter()


@router.get("/portfolio/dashboard")
def real_dashboard(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict[str, Any]:
    record = get_session(session_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is not connected.")

    account = selected_account(record)
    if account is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No account is selected.")

    configure_t_invest_sdk()
    from t_tech.invest import Client

    as_of = date.today()
    with Client(record.token) as client:
        snapshot = TInvestPortfolioAllService(client).get_portfolio_snapshot(account.account_id, as_of)

    portfolio = build_portfolio_report(
        as_of=as_of,
        account_results=[
            PortfolioAccountReport(
                account_label=account.name or account.ref,
                assets=snapshot.assets,
                total_value=snapshot.total_value,
                total_value_currency=snapshot.total_value_currency,
            )
        ],
        generated_at=snapshot.fetched_at,
    )
    return build_dashboard(
        portfolio=portfolio,
        mode="real",
        account_label=account.name or account.ref,
        cashflow_summary=None,
    )
