"""`/transactions` routes (API_SURFACE.md § 7)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import Field

from app.adapters.http.deps import get_ctx, member
from app.adapters.http.shapes import (
    ApiModel,
    Cents,
    InputModel,
    IsoDate,
    Page,
    PageParams,
    page_params,
    provided,
    trimmed,
)
from app.application import transactions as use_cases
from app.application.auth import Auth
from app.application.transactions import NewTransaction, TransactionChanges
from app.domain.transactions import BULK_DELETE_MAX, PAYEE_MAX
from app.ports import Context

router = APIRouter(prefix="/transactions", tags=["transactions"])

Payee = Annotated[str, trimmed(PAYEE_MAX)]


class TransactionOut(ApiModel):
    id: UUID
    payee: str
    budget_id: UUID
    category: str
    category_deleted: bool
    amount: int
    member_id: UUID
    date: date
    created_at: datetime
    updated_at: datetime
    archived: bool


class TransactionIn(InputModel):
    payee: Payee
    budget_id: UUID
    amount: Cents
    date: IsoDate | None = None
    member_id: UUID | None = None


class TransactionPatchIn(InputModel):
    payee: Payee | None = None
    budget_id: UUID | None = None
    amount: Cents | None = None
    date: IsoDate | None = None
    member_id: UUID | None = None


class BulkDeleteIn(InputModel):
    ids: Annotated[list[UUID], Field(min_length=1, max_length=BULK_DELETE_MAX)]


class BulkDeleteOut(ApiModel):
    deleted: list[UUID]
    not_found: list[UUID]


@router.get("")
def list_transactions(
    params: PageParams = Depends(page_params),
    _auth: Auth = Depends(member),
    ctx: Context = Depends(get_ctx),
) -> Page[TransactionOut]:
    views, total = use_cases.list_current(ctx, params.offset, params.size)
    return Page[TransactionOut](
        items=[TransactionOut.model_validate(v) for v in views],
        page=params.page,
        size=params.size,
        total=total,
    )


@router.post("", status_code=201)
def create_transaction(
    body: TransactionIn, auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> TransactionOut:
    new = NewTransaction(**body.model_dump(by_alias=False))
    return TransactionOut.model_validate(use_cases.create(ctx, auth, new))


@router.patch("/{transaction_id}")
def update_transaction(
    transaction_id: UUID,
    body: TransactionPatchIn,
    auth: Auth = Depends(member),
    ctx: Context = Depends(get_ctx),
) -> TransactionOut:
    changes = TransactionChanges(**provided(body))  # type: ignore[arg-type]
    return TransactionOut.model_validate(
        use_cases.update(ctx, auth, transaction_id, changes)
    )


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: UUID, auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> None:
    use_cases.delete(ctx, auth, transaction_id)


@router.post("/bulk-delete")
def bulk_delete(
    body: BulkDeleteIn, auth: Auth = Depends(member), ctx: Context = Depends(get_ctx)
) -> BulkDeleteOut:
    deleted, missing = use_cases.bulk_delete(ctx, auth, body.ids)
    return BulkDeleteOut(deleted=deleted, not_found=missing)
