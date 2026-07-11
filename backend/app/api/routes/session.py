from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator

from app.api.session_store import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session,
    delete_session,
    get_session,
    lookup_session,
    public_accounts,
    select_account,
    selected_account,
)
from invest_bonds.adapter import TInvestAdapter

router = APIRouter()


class ConnectRequest(BaseModel):
    token: str = Field(min_length=10, max_length=4096)

    @field_validator("token", mode="before")
    @classmethod
    def strip_token(cls, value: Any) -> str:
        return str(value).strip()


class SelectAccountRequest(BaseModel):
    account_ref: str = Field(min_length=1, max_length=64)


@router.post("/session/connect")
def connect_session(request: ConnectRequest, response: Response) -> dict[str, Any]:
    try:
        accounts = TInvestAdapter(request.token).get_accounts()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not connect T-Invest account with provided token.",
        ) from exc
    if not accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No T-Invest accounts found.")

    record = create_session(token=request.token, accounts=accounts)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=record.session_id,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return {
        "session": {
            "status": "connected",
            "expires_at": record.expires_at.isoformat().replace("+00:00", "Z"),
        },
        "accounts": public_accounts(record),
    }


@router.get("/session/status")
def session_status(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict[str, Any]:
    lookup = lookup_session(session_id)
    if lookup.status != "connected" or lookup.record is None:
        return {
            "session": {
                "status": lookup.status,
                "expires_at": None,
                "selected_account": None,
            },
            "accounts": [],
        }

    account = selected_account(lookup.record)
    return {
        "session": {
            "status": "connected",
            "expires_at": lookup.record.expires_at.isoformat().replace("+00:00", "Z"),
            "selected_account": {
                "ref": account.ref,
                "name": account.name or "Brokerage account",
            }
            if account is not None
            else None,
        },
        "accounts": public_accounts(lookup.record),
    }


@router.get("/accounts")
def get_accounts(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict[str, Any]:
    record = get_session(session_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is not connected.")
    return {"accounts": public_accounts(record)}


@router.post("/accounts/select")
def select_connected_account(
    request: SelectAccountRequest,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, Any]:
    record = get_session(session_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is not connected.")
    account = select_account(record, request.account_ref)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account reference was not found.")
    return {"accounts": public_accounts(record)}


@router.post("/session/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_session(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> None:
    delete_session(session_id)
    response.delete_cookie(SESSION_COOKIE_NAME)
