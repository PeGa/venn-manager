"""Member rules and the member view (BACKEND.md § 4.5, § 8, § 11)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Member

USERNAME_MAX = 64
REAL_NAME_MAX = 128
PASSWORD_MIN = 8
PASSWORD_MAX = 128
LANGUAGES = ("en", "es")
THEMES = ("light", "dark", "system")
AVATAR_COLORS = (
    "#d9c7a8",
    "#a9c7b6",
    "#c9bfe0",
    "#f0c9b8",
    "#bcd3e6",
    "#e6d9a3",
    "#c5dcc0",
)


def avatar_color(members_so_far: int) -> str:
    """Colors cycle through the palette in creation order."""
    return AVATAR_COLORS[members_so_far % len(AVATAR_COLORS)]


@dataclass(frozen=True)
class MemberView:
    """A member as other members see them (API_SURFACE.md § 1.2)."""

    id: UUID
    username: str
    real_name: str
    initial: str
    color: str
    role: str
    status: str
    spent_this_month: int


def member_view(member: Member, spent_this_month: int) -> MemberView:
    """Derive the public view of *member*."""
    return MemberView(
        id=member.id,
        username=member.username,
        real_name=member.real_name,
        initial=member.real_name[:1].upper(),
        color=member.color,
        role="admin" if member.is_admin else "member",
        status="removed" if member.is_removed else "active",
        spent_this_month=spent_this_month,
    )
