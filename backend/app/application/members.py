"""Member accounts, managed by admins (BACKEND.md § 8)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.application.activity import record
from app.application.auth import Auth
from app.application.common import commit_mutation, period
from app.domain.activity import Target
from app.domain.entities import Member
from app.domain.errors import DomainError, gone, not_found
from app.domain.members import MemberView, avatar_color, member_view
from app.ports import Context


@dataclass(frozen=True)
class NewMember:
    """An account to create."""

    username: str
    real_name: str
    password: str
    is_admin: bool


@dataclass(frozen=True)
class MemberChanges:
    """Fields to change. `None` means "leave as is"."""

    real_name: str | None = None
    password: str | None = None
    is_admin: bool | None = None


def _view(ctx: Context, member: Member) -> MemberView:
    current = period(ctx)
    spent = ctx.uow.transactions.spent_by_member(current.start, current.end)
    return member_view(member, spent.get(member.id, 0))


def _active(ctx: Context, member_id: UUID) -> Member:
    member = ctx.uow.members.get(member_id)
    if member is None:
        raise not_found()
    if member.is_removed:
        raise gone()
    return member


def create_member(ctx: Context, auth: Auth, new: NewMember) -> MemberView:
    """Create an account that must set its password at first sign-in."""
    if ctx.uow.members.by_username(new.username) is not None:
        raise DomainError("DUPLICATE_NAME", "Username already used", "username")
    member = Member(
        username=new.username,
        real_name=new.real_name,
        password_hash=ctx.hasher.hash(new.password),
        is_admin=new.is_admin,
        color=avatar_color(len(ctx.uow.members.all())),
        created_at=ctx.clock.now(),
    )
    ctx.uow.members.add(member)
    record(
        ctx,
        auth.member.id,
        "member.invite",
        {"name": member.real_name},
        Target("member", member.id),
    )
    commit_mutation(ctx)
    return _view(ctx, member)


def update_member(
    ctx: Context, auth: Auth, member_id: UUID, changes: MemberChanges
) -> MemberView:
    """Rename, reset the password of, or change the role of a member."""
    member = _active(ctx, member_id)
    if changes.is_admin is False and member.is_admin:
        if ctx.uow.members.active_admin_count() == 1:
            raise DomainError("LAST_ADMIN", "The household needs an admin")
    if changes.real_name is not None:
        member.real_name = changes.real_name
    if changes.is_admin is not None:
        member.is_admin = changes.is_admin
    if changes.password is not None:
        member.password_hash = ctx.hasher.hash(changes.password)
        member.must_change_password = True
        ctx.uow.sessions.delete_for_member(member.id)
    record(
        ctx,
        auth.member.id,
        "member.update",
        {"name": member.real_name},
        Target("member", member.id),
    )
    commit_mutation(ctx)
    return _view(ctx, member)


def remove_member(ctx: Context, auth: Auth, member_id: UUID) -> None:
    """Soft-remove a member and end their sessions. Their records stay."""
    member = _active(ctx, member_id)
    if member.id == auth.member.id:
        raise DomainError("SELF_REMOVAL", "Admins cannot remove themselves")
    member.is_removed = True
    ctx.uow.sessions.delete_for_member(member.id)
    record(
        ctx,
        auth.member.id,
        "member.remove",
        {"name": member.real_name},
        Target("member", member.id),
    )
    commit_mutation(ctx)
