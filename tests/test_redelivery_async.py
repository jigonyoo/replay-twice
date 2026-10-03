"""Regression tests for the review findings (REVIEW_claude_20261003):
handler errors on redelivery, and async handlers."""
import asyncio
from uuid import uuid4
import warnings

import pytest

from replay_twice import (SCENARIOS, RedeliveryErrorWarning, Replay, ReplayCase, replay_twice)
from replay_twice.examples import KINDS, SQLiteHandlers

ONCE_SCENARIOS = [s for s in SCENARIOS if s != "concurrent"]


# --- redelivery errors -------------------------------------------------------

@pytest.mark.parametrize("kind", KINDS)
def test_guarded_raises_passes_in_report_mode_but_warns(tmp_path, kind):
    store = SQLiteHandlers(tmp_path / "r.sqlite", "guarded_raises")
    with pytest.warns(RedeliveryErrorWarning, match="redelivery_errors='fail'"):
        result = Replay(repeats=2)(case_factory=lambda: store.case(kind, uuid4().hex),
                                   scenarios=SCENARIOS)
    assert result.passed
    assert all(t.observed_effects == 1 for t in result.trials)
    assert all("IntegrityError" in " ".join(t.errors) for t in result.trials)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_guarded_raises_fails_in_fail_mode(tmp_path, scenario):
    store = SQLiteHandlers(tmp_path / "r.sqlite", "guarded_raises")
    with pytest.raises(AssertionError, match=r"repetitions with handler errors=1; the handler raised \(redelivery_errors='fail'\)"):
        Replay(redelivery_errors="fail")(
            case_factory=lambda: store.case("refund", uuid4().hex), scenarios=[scenario])


def test_guarded_is_clean_in_fail_mode_without_warning(tmp_path):
    store = SQLiteHandlers(tmp_path / "g.sqlite", "guarded")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Replay(redelivery_errors="fail", repeats=3)(
            case_factory=lambda: store.case("payment.succeeded", uuid4().hex), scenarios=SCENARIOS)


def test_mode_can_be_set_per_call_and_is_validated():
    with pytest.raises(ValueError, match="redelivery_errors"):
        Replay(redelivery_errors="ignore")
    calls = []

    def handler(e):
        calls.append(e)
        if len(calls) > 1:
            raise RuntimeError("500")

    result = Replay().measure(handler, lambda k: 1 if calls else 0, "e", "k",
                              redelivery_errors="fail")
    assert not result.passed and result.trials[0].effect_ok


def test_decorator_and_cli_option_reach_the_mode(pytester):
    pytester.makepyfile('''
        from uuid import uuid4
        from replay_twice import replay_twice
        from replay_twice.examples import SQLiteHandlers

        @replay_twice(scenarios=["duplicate"], redelivery_errors="fail")
        def test_decorated(tmp_path):
            return SQLiteHandlers(tmp_path / "a.sqlite", "guarded_raises").case("refund", uuid4().hex)

        def test_fixture(replay, tmp_path):
            store = SQLiteHandlers(tmp_path / "b.sqlite", "guarded_raises")
            replay(case_factory=lambda: store.case("refund", uuid4().hex), scenarios=["duplicate"])
    ''')
    result = pytester.runpytest_subprocess("-q", "--replay-redelivery-errors=fail")
    result.assert_outcomes(failed=2)
    result = pytester.runpytest_subprocess("-q", "-k", "fixture")
    result.assert_outcomes(passed=1, warnings=1)


# --- async handlers ------------------------------------------------------------

@pytest.mark.parametrize("scenario", SCENARIOS)
def test_async_naive_really_runs_and_is_caught(tmp_path, scenario):
    # Before the fix the coroutine was never awaited: 0 effects, no error.
    store = SQLiteHandlers(tmp_path / "n.sqlite", "naive")
    result = Replay(threads=4).measure(
        case_factory=lambda: store.case("refund", uuid4().hex, mode="async"), scenarios=[scenario])
    trial = result.trials[0]
    assert trial.observed_effects == trial.deliveries > 1
    assert not trial.errors


@pytest.mark.parametrize("kind", KINDS)
def test_async_guarded_passes_everything(tmp_path, kind):
    store = SQLiteHandlers(tmp_path / "g.sqlite", "guarded")
    result = Replay(repeats=3, redelivery_errors="fail")(
        case_factory=lambda: store.case(kind, uuid4().hex, mode="async"), scenarios=SCENARIOS)
    assert len(result.trials) == 12 and all(t.observed_effects == 1 for t in result.trials)


def test_async_check_then_act_blocks_sequential_but_races_concurrently(tmp_path):
    store = SQLiteHandlers(tmp_path / "c.sqlite", "check_then_act")
    factory = lambda: store.case("refund", uuid4().hex, mode="async")
    Replay()(case_factory=factory, scenarios=ONCE_SCENARIOS)
    result = Replay(repeats=5).measure(case_factory=factory, scenarios=["concurrent"])
    assert sum(t.observed_effects > 1 for t in result.trials) >= 1


def test_async_concurrent_deliveries_overlap_on_one_loop():
    # Every delivery waits until all of them have started; sequential execution
    # would time out instead of completing.
    started, effects = [], []

    async def handler(event):
        started.append(event)
        for _ in range(200):
            if len(started) >= 6:
                break
            await asyncio.sleep(0.005)
        else:
            raise TimeoutError("deliveries did not overlap")
        effects.append(event)

    result = Replay(threads=6).measure(handler, lambda k: len(effects), "e", "e",
                                       scenarios=["concurrent"])
    assert result.trials[0].observed_effects == 6
    assert not result.trials[0].errors


def test_async_handler_inside_a_running_event_loop():
    effects = []

    async def handler(event):
        await asyncio.sleep(0)
        if event not in effects:
            effects.append(event)

    async def caller():
        return Replay()(case_factory=lambda: ReplayCase(handler, lambda k: effects.count(k),
                                                        f"k{len(effects)}", f"k{len(effects)}"),
                        scenarios=["duplicate", "timeout_retry"])

    assert asyncio.run(caller()).passed


def test_async_effects_observer_is_awaited():
    effects = []

    async def count(key):
        return effects.count(key)

    result = Replay()(lambda e: effects.append(e) if e not in effects else None, count, "a", "a")
    assert result.passed


@replay_twice(scenarios=SCENARIOS, threads=4)
def test_decorator_with_async_handler(tmp_path):
    return SQLiteHandlers(tmp_path / "d.sqlite", "guarded").case("refund", uuid4().hex, mode="async")
