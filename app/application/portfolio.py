from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.reporting.portfolio import PortfolioAccountReport, PortfolioReport, build_portfolio_report
from app.t_invest.portfolio_all import TInvestPortfolioAllService
from invest_bonds.config import load_settings
from invest_bonds.models import AccountSummary
from invest_bonds.sdk_compat import configure_t_invest_sdk


@dataclass(frozen=True)
class PortfolioRequest:
    as_of: date
    account_id: str | None = None
    include_account_id: bool = False
    generated_at: datetime | None = None


def build_t_invest_portfolio_report(request: PortfolioRequest) -> PortfolioReport:
    settings = load_settings()
    configure_t_invest_sdk()
    from t_tech.invest import Client

    with Client(settings.invest_token) as client:
        accounts = [
            AccountSummary(
                id=account.id,
                name=getattr(account, "name", ""),
                type=str(getattr(account, "type", "")),
                status=str(getattr(account, "status", "")),
                access_level=str(getattr(account, "access_level", "")),
            )
            for account in client.users.get_accounts().accounts
        ]
        selected_accounts = select_accounts(request.account_id, accounts)
        if not selected_accounts:
            raise ValueError("No T-Invest accounts found.")

        service = TInvestPortfolioAllService(client)
        account_results = []
        for index, account in enumerate(selected_accounts, start=1):
            snapshot = service.get_portfolio_snapshot(account.id, request.as_of)
            account_results.append(
                PortfolioAccountReport(
                    account_label=account_label(index, account, include_account_id=request.include_account_id),
                    account_id=account.id if request.include_account_id else None,
                    assets=snapshot.assets,
                )
            )

    return build_portfolio_report(
        as_of=request.as_of,
        account_results=account_results,
        generated_at=request.generated_at,
    )


def select_accounts(account_id: str | None, accounts: list[AccountSummary]) -> list[AccountSummary]:
    if account_id:
        matching = [account for account in accounts if account.id == account_id]
        return matching or [AccountSummary(id=account_id)]
    return accounts


def account_label(index: int, account: AccountSummary, *, include_account_id: bool) -> str:
    if include_account_id:
        if account.name:
            return f"{account.name} ({account.id})"
        return account.id
    return f"account_{index}"
