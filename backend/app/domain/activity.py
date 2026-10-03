"""Activity targets and the merge rule (BACKEND.md § 9)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Activity


@dataclass(frozen=True)
class Target:
    """What an entry points at: a record, a settings section, or nothing."""

    type: str
    id: UUID | None = None
    section: str | None = None

    @property
    def is_none(self) -> bool:
        """Entries without a target never merge."""
        return self.type == "none"


NO_TARGET = Target("none")


def merges_into(
    newest: Activity | None, actor_id: UUID, action: str, target: Target
) -> bool:
    """Whether a new entry should update *newest* instead of adding a row."""
    return (
        newest is not None
        and not target.is_none
        and newest.actor_id == actor_id
        and newest.action == action
        and newest.target_type == target.type
        and newest.target_id == target.id
        and newest.target_section == target.section
    )
