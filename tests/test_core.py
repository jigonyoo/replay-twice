from collections import Counter
from threading import Lock
from uuid import uuid4

import pytest

from replay_twice import Replay, ReplayCase, SCENARIOS, LoseFirstReply, ScriptedAgent
from replay_twice.examples import SQLiteHandlers, KINDS


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_naive_is_detected(tmp_path, kind, scenario):
    store = SQLiteHandlers(tmp_path / "naive.sqlite", "naive")
    case = store.case(kind, uuid4().hex)
    with pytest.raises(AssertionError, match=rf"{scenario}: failed 1/1 repetitions") as failure:
        Replay()(case.handler, case.effects, case.event, case.key, scenarios=[scenario])
    assert "deliveries" in str(failure.value)
    assert "observed effects" in str(failure.value)


@pytest.mark.parametrize("kind", KINDS)
def test_guarded_all_scenarios(tmp_path, kind):
    store = SQLiteHandlers(tmp_path / "guarded.sqlite", "guarded")
    result = Replay(repeats=5)(case_factory=lambda: store.case(kind, uuid4().hex), scenarios=SCENARIOS)
    assert result.passed
    assert len(result.trials) == 20
    assert all(t.observed_effects == 1 for t in result.trials)


@pytest.mark.parametrize("kind", KINDS)
def test_check_then_act_sequential_only(tmp_path, kind):
    store = SQLiteHandlers(tmp_path / "check.sqlite", "check_then_act")
    Replay()(case_factory=lambda: store.case(kind, uuid4().hex),
             scenarios=[s for s in SCENARIOS if s != "concurrent"])


def test_concurrent_barrier_creates_real_overlap():
    # The inner rendezvous cannot complete if deliveries are sequential.
    from threading import Barrier
    rendezvous = Barrier(8)
    counter = Counter()
    lock = Lock()
    def handler(key):
        rendezvous.wait(timeout=5)
        with lock:
            counter[key] += 1
    result = Replay().measure(handler, lambda k: counter[k], "order", "order", scenarios=["concurrent"])
    assert not result.passed
    assert result.trials[0].observed_effects == 8
    assert result.trials[0].deliveries == 8
    assert not result.trials[0].errors


def test_agent_timeout_happens_after_commit_and_reuses_arguments():
    events = []
    event = {"order_id": "order"}
    def tool(argument):
        events.append(argument)
        return "receipt"
    transport = LoseFirstReply(tool)
    with pytest.raises(TimeoutError):
        transport(event)
    assert events == [event]
    assert transport(event) == "receipt"
    assert events[0] is events[1]
    agent = ScriptedAgent()
    assert agent.run(LoseFirstReply(tool), event) == "receipt"
    assert agent.trace == ["tool_call", "timeout", "retry_same_arguments", "tool_call", "tool_result"]


def test_effect_count_is_the_verdict_and_handler_errors_remain_visible():
    with pytest.raises(AssertionError, match="observed effects=\\[0\\]"):
        Replay()(lambda e: None, lambda k: 0, "event", "key")
    counter = Counter()
    def handler(key):
        counter[key] = 1
        raise RuntimeError("real handler failure")
    result = Replay().measure(handler, lambda k: counter[k], "key", "key")
    assert result.passed  # The requested invariant is the actual effect count.
    assert len(result.trials[0].errors) == 2


def test_failure_message_counts_all_repetitions():
    def fresh():
        counter = Counter()
        return ReplayCase(lambda k: counter.update([k]), lambda k: counter[k], "key", "key")
    result = Replay(repeats=3).measure(case_factory=fresh)
    with pytest.raises(AssertionError, match="failed 3/3 repetitions"):
        result.assert_passed()


@pytest.mark.parametrize("options", [{"threads": 1}, {"threads": True}, {"repeats": 0}])
def test_invalid_configuration(options):
    with pytest.raises(ValueError):
        Replay(**options)


def test_factory_is_required_for_multiple_trials_and_clean_state():
    with pytest.raises(ValueError, match="case_factory"):
        Replay(repeats=2).measure(lambda e: None, lambda k: 0, "event", "key")
    with pytest.raises(ValueError, match="unused key"):
        Replay().measure(case_factory=lambda: ReplayCase(lambda e: None, lambda k: 1, "e", "k"))
    with pytest.raises(ValueError, match="distinct scenarios"):
        Replay().measure(case_factory=lambda: None, scenarios=["typo"])


def test_guard_claim_and_effect_roll_back_together(tmp_path):
    import sqlite3
    store = SQLiteHandlers(tmp_path / "rollback.sqlite", "guarded")
    connection = sqlite3.connect(store.database)
    connection.execute("CREATE TRIGGER broken BEFORE INSERT ON ledger BEGIN SELECT RAISE(ABORT, 'broken'); END")
    connection.commit()
    with pytest.raises(sqlite3.IntegrityError):
        store.refund("key", 800)
    assert store.effects("refund", "key") == 0
    assert connection.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 0
    connection.execute("DROP TRIGGER broken")
    connection.commit()
    connection.close()
    assert store.refund("key", 800) == "applied"
    assert store.effects("refund", "key") == 1
