"""`/members` routes, admin only (API_SURFACE.md § 5)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import StrictBool

from app.adapters.http.deps import admin, get_ctx
from app.adapters.http.shapes import InputModel, MemberOut, Password, provided, trimmed
from app.application import members as use_cases
from app.application.auth import Auth
from app.application.members import MemberChanges, NewMember
from app.domain.members import REAL_NAME_MAX, USERNAME_MAX
from app.ports import Context

router = APIRouter(prefix="/members", tags=["members"])


class MemberIn(InputModel):
    username: Annotated[str, trimmed(USERNAME_MAX)]
    real_name: Annotated[str, trimmed(REAL_NAME_MAX)]
    password: Password
    is_admin: StrictBool


class MemberPatchIn(InputModel):
    real_name: Annotated[str, trimmed(REAL_NAME_MAX)] | None = None
    password: Password | None = None
    is_admin: StrictBool | None = None


@router.post("", status_code=201)
def create_member(
    body: MemberIn, auth: Auth = Depends(admin), ctx: Context = Depends(get_ctx)
) -> MemberOut:
    new = NewMember(**body.model_dump(by_alias=False))
    return MemberOut.model_validate(use_cases.create_member(ctx, auth, new))


@router.patch("/{member_id}")
def update_member(
    member_id: UUID,
    body: MemberPatchIn,
    auth: Auth = Depends(admin),
    ctx: Context = Depends(get_ctx),
) -> MemberOut:
    changes = MemberChanges(**provided(body))  # type: ignore[arg-type]
    return MemberOut.model_validate(
        use_cases.update_member(ctx, auth, member_id, changes)
    )


@router.delete("/{member_id}", status_code=204)
def remove_member(
    member_id: UUID, auth: Auth = Depends(admin), ctx: Context = Depends(get_ctx)
) -> None:
    use_cases.remove_member(ctx, auth, member_id)
