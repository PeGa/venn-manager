"""`/me` route (API_SURFACE.md § 3)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends

from app.adapters.http.deps import get_ctx, member
from app.adapters.http.shapes import InputModel, SessionOut, provided, trimmed
from app.application.auth import Auth
from app.application.me import ProfileChanges, update_me
from app.domain.members import REAL_NAME_MAX, USERNAME_MAX
from app.ports import Context

router = APIRouter(tags=["me"])


class MeIn(InputModel):
    username: Annotated[str, trimmed(USERNAME_MAX)] | None = None
    real_name: Annotated[str, trimmed(REAL_NAME_MAX)] | None = None
    language: Literal["en", "es"] | None = None
    theme: Literal["light", "dark", "system"] | None = None


@router.patch("/me")
def patch_me(
    body: MeIn, auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> SessionOut:
    changes = ProfileChanges(**provided(body))  # type: ignore[arg-type]
    return SessionOut.of(update_me(ctx, auth, changes))
