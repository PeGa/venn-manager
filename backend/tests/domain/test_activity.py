"""The activity merge rule (BACKEND.md § 9)."""

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.activity import NO_TARGET, Target, merges_into
from app.domain.entities import Activity

ACTOR = uuid4()
BUDGET = uuid4()


def _entry(**overrides: object) -> Activity:
    values: dict[str, object] = {
        "actor_id": ACTOR,
        "action": "budget.amount",
        "at": datetime(2026, 9, 1, tzinfo=UTC),
        "target_type": "budget",
        "target_id": BUDGET,
    }
    values.update(overrides)
    return Activity(**values)  # type: ignore[arg-type]


def test_merges_into_same_actor_action_and_target() -> None:
    assert merges_into(_entry(), ACTOR, "budget.amount", Target("budget", BUDGET))


def test_merges_into_nothing_when_feed_is_empty() -> None:
    assert not merges_into(None, ACTOR, "budget.amount", Target("budget", BUDGET))


def test_merges_into_rejects_other_actor_action_or_target() -> None:
    target = Target("budget", BUDGET)
    assert not merges_into(_entry(), uuid4(), "budget.amount", target)
    assert not merges_into(_entry(), ACTOR, "budget.rename", target)
    assert not merges_into(_entry(), ACTOR, "budget.amount", Target("budget", uuid4()))


def test_merges_into_never_merges_targetless_entries() -> None:
    newest = _entry(action="tx.bulkDelete", target_type="none", target_id=None)
    assert not merges_into(newest, ACTOR, "tx.bulkDelete", NO_TARGET)
