from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, status

from app.api.services.dashboard import build_dashboard, position_sort_key
from app.api.session_store import SESSION_COOKIE_NAME, get_session, selected_account, selected_accounts
from app.reporting.portfolio import PortfolioAccountReport, PortfolioReport, build_portfolio_report
from app.reporting.serializers.cashflow_json import iso_datetime
from app.reporting.serializers.portfolio_json import asset_to_dict
from app.t_invest.portfolio_all import TInvestPortfolioAllService
from invest_bonds.sdk_compat import configure_t_invest_sdk

router = APIRouter()


@dataclass(frozen=True)
class SelectedPortfolio:
    account_label: str
    portfolio: PortfolioReport


@router.get("/portfolio/dashboard")
def real_dashboard(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict[str, Any]:
    selected = load_selected_portfolio(session_id)
    return build_dashboard(
        portfolio=selected.portfolio,
        mode="real",
        account_label=selected.account_label,
        cashflow_summary=None,
    )


@router.get("/portfolio/positions")
def portfolio_positions(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict[str, Any]:
    selected = load_selected_portfolio(session_id)
    positions = sorted(
        (asset for account in selected.portfolio.accounts for asset in account.assets),
        key=position_sort_key,
        reverse=True,
    )
    return {
        "schema_version": "1.0",
        "report_type": "portfolio_positions",
        "generated_at": iso_datetime(selected.portfolio.generated_at),
        "as_of": selected.portfolio.as_of.isoformat(),
        "account_label": selected.account_label,
        "positions": [asset_to_dict(asset) for asset in positions],
        "warnings": selected.portfolio.warnings,
    }


def load_selected_portfolio(session_id: str | None) -> SelectedPortfolio:
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
        snapshots = []
        warnings = []
        for session_account in accounts:
            try:
                snapshots.append((session_account, service.get_portfolio_snapshot(session_account.account_ids[0], as_of)))
            except Exception:
                warnings.append(f"Could not load portfolio data for {session_account.ref}.")

    if not snapshots:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Portfolio data is unavailable for all selected accounts.",
        )

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
        warnings=warnings,
    )
    return SelectedPortfolio(account_label=account.name or account.ref, portfolio=portfolio)
