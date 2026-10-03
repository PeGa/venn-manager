"""Member view and colors (BACKEND.md § 11, API_SURFACE.md § 1.2)."""

from datetime import UTC, datetime

from app.domain.entities import Member
from app.domain.members import AVATAR_COLORS, avatar_color, member_view


def _member(**overrides: object) -> Member:
    values: dict[str, object] = {
        "username": "priya",
        "real_name": "priya Okafor",
        "password_hash": "x",
        "is_admin": False,
        "color": "#d9c7a8",
        "created_at": datetime(2026, 9, 1, tzinfo=UTC),
    }
    values.update(overrides)
    return Member(**values)  # type: ignore[arg-type]


def test_member_view_derives_initial_role_and_status() -> None:
    view = member_view(_member(), spent_this_month=8412)
    assert view.initial == "P"
    assert view.role == "member"
    assert view.status == "active"
    assert view.spent_this_month == 8412


def test_member_view_of_removed_admin() -> None:
    view = member_view(_member(is_admin=True, is_removed=True), 0)
    assert view.role == "admin"
    assert view.status == "removed"


def test_avatar_color_cycles_through_the_palette() -> None:
    assert avatar_color(0) == AVATAR_COLORS[0]
    assert avatar_color(len(AVATAR_COLORS)) == AVATAR_COLORS[0]
    assert avatar_color(8) == AVATAR_COLORS[1]
