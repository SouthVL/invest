from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, status

from app.api.services.dashboard import build_dashboard
from app.api.session_store import SESSION_COOKIE_NAME, get_session, selected_account, selected_accounts
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
    accounts = selected_accounts(record)
    if not accounts:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No account is selected.")

    configure_t_invest_sdk()
    from t_tech.invest import Client

    as_of = date.today()
    with Client(record.token) as client:
        service = TInvestPortfolioAllService(client)
        snapshots = [
            (session_account, service.get_portfolio_snapshot(session_account.account_ids[0], as_of)) for session_account in accounts
        ]

    portfolio = build_portfolio_report(
        as_of=as_of,
        account_results=[
            PortfolioAccountReport(
                account_label=session_account.name or session_account.ref,
                assets=snapshot.assets,
                total_value=snapshot.total_value,
                total_value_currency=snapshot.total_value_currency,
            )
            for session_account, snapshot in snapshots
        ],
        generated_at=snapshots[-1][1].fetched_at,
    )
    return build_dashboard(
        portfolio=portfolio,
        mode="real",
        account_label=account.name or account.ref,
        cashflow_summary=None,
    )
