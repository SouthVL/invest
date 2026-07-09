from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from threading import Lock
from typing import Any

from invest_bonds.models import AccountSummary

SESSION_COOKIE_NAME = "south_invest_session"
SESSION_MAX_AGE_SECONDS = 30 * 60


@dataclass(frozen=True)
class SessionAccount:
    ref: str
    account_id: str
    name: str
    type: str
    status: str


@dataclass
class SessionRecord:
    session_id: str
    token: str
    accounts: list[SessionAccount]
    selected_account_ref: str | None
    expires_at: datetime


_sessions: dict[str, SessionRecord] = {}
_lock = Lock()


def create_session(*, token: str, accounts: list[AccountSummary]) -> SessionRecord:
    session_id = token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=SESSION_MAX_AGE_SECONDS)
    session_accounts = [
        SessionAccount(
            ref=f"account_{index}",
            account_id=account.id,
            name=account.name,
            type=account.type,
            status=account.status,
        )
        for index, account in enumerate(accounts, start=1)
    ]
    record = SessionRecord(
        session_id=session_id,
        token=token,
        accounts=session_accounts,
        selected_account_ref=session_accounts[0].ref if session_accounts else None,
        expires_at=expires_at,
    )
    with _lock:
        _sessions[session_id] = record
    return record


def get_session(session_id: str | None) -> SessionRecord | None:
    if not session_id:
        return None
    with _lock:
        record = _sessions.get(session_id)
        if record is None:
            return None
        if record.expires_at <= datetime.now(UTC):
            del _sessions[session_id]
            return None
        return record


def delete_session(session_id: str | None) -> None:
    if not session_id:
        return
    with _lock:
        _sessions.pop(session_id, None)


def select_account(record: SessionRecord, account_ref: str) -> SessionAccount | None:
    account = get_account(record, account_ref)
    if account is None:
        return None
    with _lock:
        record.selected_account_ref = account.ref
    return account


def selected_account(record: SessionRecord) -> SessionAccount | None:
    if record.selected_account_ref is None:
        return None
    return get_account(record, record.selected_account_ref)


def get_account(record: SessionRecord, account_ref: str) -> SessionAccount | None:
    return next((account for account in record.accounts if account.ref == account_ref), None)


def public_accounts(record: SessionRecord) -> list[dict[str, Any]]:
    return [
        {
            "ref": account.ref,
            "name": account.name or "Brokerage account",
            "type": account.type,
            "status": account.status,
            "masked_id": mask_account_id(account.account_id),
            "selected": account.ref == record.selected_account_ref,
        }
        for account in record.accounts
    ]


def mask_account_id(account_id: str) -> str:
    if len(account_id) <= 4:
        return "****"
    return f"****{account_id[-4:]}"


def clear_sessions() -> None:
    with _lock:
        _sessions.clear()
