"""Regression tests for the second independent review of v0.2."""
import asyncio
import functools
import warnings
from uuid import uuid4

import pytest

from replay_twice import RedeliveryErrorWarning, Replay, ReplayCase, SCENARIOS
from replay_twice.examples import SQLiteHandlers


class LockedTool:
    """Correct in one process: an asyncio.Lock guards check-then-write.
    The lock is created once and reused, so it is bound to the first loop it meets."""

    def __init__(self):
        self.lock = asyncio.Lock()
        self.done = []

    async def __call__(self, event):
        async with self.lock:
            if event in self.done:
                return "already"
            await asyncio.sleep(0.001)
            self.done.append(event)

    def effects(self, key):
        return self.done.count(key)


def test_loop_bound_state_survives_many_trials_and_scenarios():
    tool = LockedTool()
    n = iter(range(10_000))

    def fresh():
        key = f"k{next(n)}"
        return ReplayCase(tool, tool.effects, key, key)

    result = Replay(threads=4, repeats=3, redelivery_errors="fail")(case_factory=fresh,
                                                                    scenarios=SCENARIOS)
    assert all(not t.errors for t in result.trials)


def test_cached_loop_client_is_not_closed_between_calls():
    class Client:
        loop = None
        rows = []

        async def __call__(self, event):
            loop = asyncio.get_running_loop()
            if Client.loop is None:
                Client.loop = loop
            assert loop is Client.loop and not loop.is_closed(), "loop changed"
            await asyncio.sleep(0)
            if event not in Client.rows:
                Client.rows.append(event)

    c = Client()
    Replay()(case_factory=lambda: ReplayCase(c, Client.rows.count, e := uuid4().hex, e),
             scenarios=["duplicate", "timeout_retry", "crash_before_ack"])


def test_first_delivery_error_after_commit_is_inconclusive_not_a_pass():
    seen = []

    def handler(e):
        seen.append(e)
        raise ConnectionError("reply failed after commit")

    result = Replay().measure(handler, seen.count, "e", "e", scenarios=["timeout_retry"])
    trial = result.trials[0]
    assert trial.deliveries == 1 and trial.effect_ok and not trial.passed
    assert "no redelivery happened" in trial.inconclusive
    with pytest.raises(AssertionError, match="inconclusive: no redelivery happened"):
        result.assert_passed()


def test_blocking_async_handler_is_inconclusive_for_concurrent(tmp_path):
    store = SQLiteHandlers(tmp_path / "c.sqlite", "check_then_act", race_delay=0.01)

    async def blocking_refund(event):          # sync SQLite call inside async def
        return store.refund_event(event)

    def fresh():
        key = uuid4().hex
        return ReplayCase(blocking_refund, lambda k: store.effects("refund", k),
                          {"order_id": key, "amount": 1}, key)

    result = Replay(threads=8).measure(case_factory=fresh, scenarios=["concurrent"])
    trial = result.trials[0]
    assert trial.max_in_flight == 1 and not trial.passed
    assert "did not overlap" in trial.inconclusive


def test_yielding_async_handler_reports_real_overlap(tmp_path):
    store = SQLiteHandlers(tmp_path / "g.sqlite", "guarded")
    result = Replay(threads=8)(case_factory=lambda: store.case("refund", uuid4().hex, mode="async"),
                               scenarios=["concurrent"])
    assert result.trials[0].max_in_flight == 8


def test_injected_errors_are_never_reported_as_handler_errors():
    calls, rows = [], []

    def handler(e):                       # first call times out for real, without committing
        calls.append(e)
        if len(calls) == 1:
            raise TimeoutError("real upstream timeout")
        if e not in rows:
            rows.append(e)

    trial = Replay().measure(handler, rows.count, "e", "e", scenarios=["timeout_retry"]).trials[0]
    assert trial.errors == ("TimeoutError: real upstream timeout",)
    assert not any("injected" in err for err in trial.errors)


def test_crash_before_ack_reports_only_the_handler_error():
    calls, rows = [], []

    def handler(e):
        calls.append(e)
        if len(calls) == 1:
            raise ValueError("first delivery broke before commit")
        if e not in rows:
            rows.append(e)

    trial = Replay().measure(handler, rows.count, "e", "e", scenarios=["crash_before_ack"]).trials[0]
    assert trial.errors == ("ValueError: first delivery broke before commit",)


def test_cancelled_error_is_recorded_not_raised():
    rows = []

    async def handler(e):
        if e in rows:
            raise asyncio.CancelledError()
        rows.append(e)

    trial = Replay().measure(handler, rows.count, "e", "e", scenarios=["duplicate"]).trials[0]
    assert trial.errors == ("CancelledError: ",)


def test_async_case_factory_is_awaited(tmp_path):
    store = SQLiteHandlers(tmp_path / "f.sqlite", "guarded")

    async def factory():
        return store.case("refund", uuid4().hex)

    assert Replay()(case_factory=factory, scenarios=["duplicate"]).passed


def test_observer_returning_none_is_a_type_error_not_a_dirty_key():
    with pytest.raises(TypeError, match="nonnegative integer, got None"):
        Replay().measure(lambda e: None, lambda k: None, "e", "e")


def test_partial_and_coroutine_returning_handlers():
    rows = []

    async def apply(prefix, e):
        await asyncio.sleep(0)
        if e not in rows:
            rows.append(e)

    Replay()(functools.partial(apply, "x"), rows.count, "p", "p")
    Replay()(lambda e: apply("y", e), rows.count, "q", "q")


def test_warning_points_at_the_calling_test(tmp_path):
    store = SQLiteHandlers(tmp_path / "w.sqlite", "guarded_raises")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Replay()(case_factory=lambda: store.case("refund", uuid4().hex), scenarios=["duplicate"])
    (w,) = [w for w in caught if issubclass(w.category, RedeliveryErrorWarning)]
    assert w.filename == __file__


def test_no_warning_when_the_effect_check_fails():
    rows = []

    def handler(e):
        rows.append(e)
        raise RuntimeError("and it raised")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(AssertionError):
            Replay()(handler, rows.count, "e", "e")


def test_cli_options_reach_the_decorator(pytester):
    pytester.makepyfile('''
        from uuid import uuid4
        from replay_twice import replay_twice, ReplayCase
        from replay_twice.examples import SQLiteHandlers

        @replay_twice(scenarios=["duplicate"])
        def test_cli_mode(tmp_path):
            return SQLiteHandlers(tmp_path / "a.sqlite", "guarded_raises").case("refund", uuid4().hex)

        @replay_twice(scenarios=["duplicate"])
        def test_cli_repeats():
            rows = []
            return ReplayCase(lambda e: rows.append(e), rows.count, "e", "e")

        @replay_twice(scenarios=["duplicate"], redelivery_errors="report")
        def test_explicit_wins(tmp_path):
            return SQLiteHandlers(tmp_path / "b.sqlite", "guarded_raises").case("refund", uuid4().hex)
    ''')
    result = pytester.runpytest_subprocess("-q", "--replay-redelivery-errors=fail",
                                           "--replay-repeats=3")
    result.assert_outcomes(failed=2, passed=1)
    result.stdout.fnmatch_lines(["*duplicate: failed 3/3 repetitions*"])


def test_decorator_keeps_fixtures_parametrize_and_request(pytester):
    pytester.makepyfile('''
        import pytest
        from replay_twice import replay_twice, ReplayCase

        @pytest.fixture
        def store():
            return []

        @pytest.mark.parametrize("n", [1, 2])
        @replay_twice(scenarios=["duplicate", "timeout_retry"])
        def test_with_fixture(store, n, request):
            assert request.node.name.startswith("test_with_fixture")
            key = f"k{n}{len(store)}"
            return ReplayCase(lambda e: None if e in store else store.append(e), store.count, key, key)

        @replay_twice(scenarios=["duplicate"])
        async def test_async_factory():
            rows = []
            return ReplayCase(lambda e: None if e in rows else rows.append(e), rows.count, "a", "a")
    ''')
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=3)
