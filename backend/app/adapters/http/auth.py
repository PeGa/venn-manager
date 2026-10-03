"""`/auth` routes (API_SURFACE.md § 2)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import StringConstraints

from app.adapters.http.deps import (
    COOKIE_NAME,
    authenticated,
    get_ctx,
    get_settings,
    member,
)
from app.adapters.http.shapes import InputModel, Password, SessionOut
from app.application import auth as use_cases
from app.application.auth import Auth
from app.config import Settings
from app.ports import Context

router = APIRouter(prefix="/auth", tags=["auth"])

Credential = Annotated[str, StringConstraints(strict=True, max_length=256)]


class LoginIn(InputModel):
    username: Credential
    password: Credential


class PasswordIn(InputModel):
    current_password: Credential
    new_password: Password


@router.post("/login")
def login(
    body: LoginIn,
    response: Response,
    ctx: Context = Depends(get_ctx),
    settings: Settings = Depends(get_settings),
) -> SessionOut:
    token, view = use_cases.login(ctx, body.username, body.password)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        path="/",
    )
    return SessionOut.of(view)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    auth: Auth = Depends(authenticated),
    ctx: Context = Depends(get_ctx),
) -> None:
    use_cases.logout(ctx, auth)
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/session")
def session(
    auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> SessionOut:
    return SessionOut.of(use_cases.session_view(ctx, auth.member))


@router.post("/password", status_code=204)
def change_password(
    body: PasswordIn,
    auth: Auth = Depends(authenticated),
    ctx: Context = Depends(get_ctx),
) -> None:
    use_cases.change_password(ctx, auth, body.current_password, body.new_password)
