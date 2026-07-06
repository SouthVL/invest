from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.reporting.offers import OffersAccountReport, OffersReport, build_offers_report
from app.t_invest.bond_offers import TInvestBondOfferService
from invest_bonds.config import load_settings
from invest_bonds.models import AccountSummary
from invest_bonds.sdk_compat import configure_t_invest_sdk


@dataclass(frozen=True)
class OffersRequest:
    as_of: date
    days: int = 180
    warning_days: int = 45
    account_id: str | None = None
    include_account_id: bool = False
    generated_at: datetime | None = None


def build_t_invest_offers_report(request: OffersRequest) -> OffersReport:
    if request.days < 1:
        raise ValueError("--days must be at least 1")
    if request.warning_days < 0:
        raise ValueError("--warning-days must be non-negative")

    settings = load_settings()
    configure_t_invest_sdk()
    from t_tech.invest import Client

    to_date = date.fromordinal(request.as_of.toordinal() + request.days)
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

        service = TInvestBondOfferService(client)
        account_results = []
        for index, account in enumerate(selected_accounts, start=1):
            offers = service.get_upcoming_offers(
                account_id=account.id,
                from_date=request.as_of,
                to_date=to_date,
                warning_days=request.warning_days,
            )
            account_results.append(
                OffersAccountReport(
                    account_label=account_label(index, account, include_account_id=request.include_account_id),
                    account_id=account.id if request.include_account_id else None,
                    offers=offers,
                )
            )

    return build_offers_report(
        as_of=request.as_of,
        days=request.days,
        warning_days=request.warning_days,
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
