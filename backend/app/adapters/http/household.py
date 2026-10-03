"""`/household` routes (API_SURFACE.md § 4)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import StrictBool, StringConstraints

from app.adapters.http.deps import get_ctx, member
from app.adapters.http.shapes import (
    ApiModel,
    Cents,
    InputModel,
    MemberOut,
    provided,
    trimmed,
)
from app.application.auth import Auth
from app.application.household import HouseholdChanges, household_view, update_household
from app.domain.household import CURRENCY_SIGN_MAX, HOUSEHOLD_NAME_MAX
from app.ports import Context

router = APIRouter(prefix="/household", tags=["household"])


class HouseholdOut(ApiModel):
    name: str
    currency_sign: str
    timezone: str
    opening_balance: int
    show_member_income: bool
    members: list[MemberOut]


class HouseholdIn(InputModel):
    name: Annotated[str, trimmed(HOUSEHOLD_NAME_MAX)] | None = None
    currency_sign: (
        Annotated[
            str,
            StringConstraints(
                strict=True, strip_whitespace=True, max_length=CURRENCY_SIGN_MAX
            ),
        ]
        | None
    ) = None
    timezone: Annotated[str, trimmed(64)] | None = None
    opening_balance: Cents | None = None
    show_member_income: StrictBool | None = None


@router.get("")
def get_household(
    _auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> HouseholdOut:
    return HouseholdOut.model_validate(household_view(ctx))


@router.patch("")
def patch_household(
    body: HouseholdIn, auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> HouseholdOut:
    changes = HouseholdChanges(**provided(body))  # type: ignore[arg-type]
    return HouseholdOut.model_validate(update_household(ctx, auth, changes))
