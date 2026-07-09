from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.analytics.cashflow_forecast import _add_months, build_monthly_cashflow
from app.reporting.cashflow import CashflowAccountReport, CashflowReport, build_cashflow_report
from app.t_invest.cashflow import TInvestCashflowService
from invest_bonds.config import load_settings
from invest_bonds.models import AccountSummary
from invest_bonds.sdk_compat import configure_t_invest_sdk


@dataclass(frozen=True)
class CashflowRequest:
    months: int
    as_of: date
    account_id: str | None = None
    report_currency: str = "RUB"
    repeat_floating_last_coupon: bool = False
    include_account_id: bool = False
    generated_at: datetime | None = None


def build_t_invest_cashflow_report(request: CashflowRequest) -> CashflowReport:
    if request.months < 1:
        raise ValueError("--months must be at least 1")

    settings = load_settings()
    configure_t_invest_sdk()
    from t_tech.invest import Client

    start_date = request.as_of
    to_date = _add_months(date(start_date.year, start_date.month, 1), request.months)
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

        service = TInvestCashflowService(client)
        account_results = []
        for index, account in enumerate(selected_accounts, start=1):
            events = service.get_portfolio_cashflow_events(
                account_id=account.id,
                from_date=start_date,
                to_date=to_date,
                repeat_floating_last_coupon=request.repeat_floating_last_coupon,
                report_currency=request.report_currency.upper(),
            )
            rows = build_monthly_cashflow(
                events,
                start_date=start_date,
                months=request.months,
                currency=request.report_currency.upper(),
            )
            account_results.append(
                CashflowAccountReport(
                    account_label=account_label(index, account, include_account_id=request.include_account_id),
                    account_id=account.id if request.include_account_id else None,
                    monthly=rows,
                    events=events,
                )
            )

    return build_cashflow_report(
        as_of=start_date,
        months=request.months,
        report_currency=request.report_currency.upper(),
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
