"""Member and session shapes (API_SURFACE.md § 1.2, § 1.11)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import StringConstraints

from app.models.user import REAL_NAME_MAX, USERNAME_MAX
from app.schemas.common import ApiModel

Username = Annotated[
    str,
    StringConstraints(
        strict=True, strip_whitespace=True, min_length=1, max_length=USERNAME_MAX
    ),
]
RealName = Annotated[
    str,
    StringConstraints(
        strict=True, strip_whitespace=True, min_length=1, max_length=REAL_NAME_MAX
    ),
]
Language = Literal["en", "es"]
Theme = Literal["light", "dark", "system"]


class MemberOut(ApiModel):
    """A member as every other member sees them."""

    id: uuid.UUID
    username: str
    real_name: str
    initial: str
    color: str
    role: Literal["admin", "member"]
    status: Literal["active", "removed"]
    spent_this_month: int


class PreferencesOut(ApiModel):
    """Per-member display preferences. `language` null means follow the browser."""

    language: Language | None
    theme: Theme


class SessionOut(ApiModel):
    """The signed-in member and what the client needs to render for them."""

    member: MemberOut
    must_change_password: bool
    preferences: PreferencesOut
