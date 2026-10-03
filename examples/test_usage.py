"""Runnable fixture and decorator examples; every trial has a fresh key."""
from uuid import uuid4

from replay_twice import SCENARIOS, replay_twice
from replay_twice.examples import SQLiteHandlers


def test_fixture(replay, tmp_path):
    store = SQLiteHandlers(tmp_path / "fixture.sqlite", "guarded")
    replay(case_factory=lambda: store.case("refund", uuid4().hex), scenarios=SCENARIOS)


@replay_twice(scenarios=SCENARIOS)
def test_decorator(tmp_path):
    store = SQLiteHandlers(tmp_path / "decorator.sqlite", "guarded")
    return store.case("payment.succeeded", uuid4().hex)
