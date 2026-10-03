"""Sign-in, sessions and passwords (BACKEND.md § 8)."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.common import period
from app.domain.entities import LoginSession, Member
from app.domain.errors import DomainError, validation
from app.domain.members import MemberView, member_view
from app.ports import Context


@dataclass(frozen=True)
class SessionView:
    """The signed-in member and their preferences (API_SURFACE.md § 1.11)."""

    member: MemberView
    must_change_password: bool
    language: str | None
    theme: str


@dataclass(frozen=True)
class Auth:
    """The member behind a request and the session they used."""

    member: Member
    session: LoginSession


def session_view(ctx: Context, member: Member) -> SessionView:
    """Shape *member* for the session endpoints."""
    current = period(ctx)
    spent = ctx.uow.transactions.spent_by_member(current.start, current.end)
    return SessionView(
        member=member_view(member, spent.get(member.id, 0)),
        must_change_password=member.must_change_password,
        language=member.language,
        theme=member.theme,
    )


def login(ctx: Context, username: str, password: str) -> tuple[str, SessionView]:
    """Start a session. Unknown, removed and wrong-password logins look alike."""
    member = ctx.uow.members.by_username(username)
    if (
        member is None
        or member.is_removed
        or not ctx.hasher.verify(member.password_hash, password)
    ):
        raise DomainError("UNAUTHORIZED", "Invalid username or password")
    token = ctx.tokens.new_token()
    ctx.uow.sessions.add(
        LoginSession(
            token_hash=ctx.tokens.digest(token),
            user_id=member.id,
            created_at=ctx.clock.now(),
        )
    )
    ctx.uow.commit()
    return token, session_view(ctx, member)


def authenticate(ctx: Context, token: str | None) -> Auth:
    """Resolve a cookie token. Any valid session passes, even a restricted one."""
    found = ctx.uow.sessions.find(ctx.tokens.digest(token)) if token else None
    if found is None:
        raise DomainError("UNAUTHORIZED", "No active session")
    return Auth(member=found[1], session=found[0])


def require_usable(auth: Auth) -> Auth:
    """Block restricted sessions (BACKEND.md § 8.4)."""
    if auth.member.must_change_password:
        raise DomainError("PASSWORD_CHANGE_REQUIRED", "Password change required")
    return auth


def require_admin(auth: Auth) -> Auth:
    """Block non-admins (BACKEND.md § 8.1)."""
    if not auth.member.is_admin:
        raise DomainError("FORBIDDEN", "Admins only")
    return auth


def logout(ctx: Context, auth: Auth) -> None:
    """End this session only."""
    ctx.uow.sessions.delete(auth.session)
    ctx.uow.commit()


def change_password(ctx: Context, auth: Auth, current: str, new: str) -> None:
    """Set a new password, clear the forced-change flag, end other sessions.

    The new password may equal the current one (BACKEND.md § 8.3).
    """
    if not ctx.hasher.verify(auth.member.password_hash, current):
        raise validation("Current password is wrong", "currentPassword")
    auth.member.password_hash = ctx.hasher.hash(new)
    auth.member.must_change_password = False
    ctx.uow.sessions.delete_for_member(auth.member.id, keep=auth.session.id)
    ctx.uow.commit()
