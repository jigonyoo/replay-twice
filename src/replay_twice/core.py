"""Replay drills. Each trial observes the absolute effect count for its key."""
import asyncio
import inspect
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Barrier
from typing import Any, Callable, Iterable

from .agent import CrashBeforeAck, LoseFirstReply, ScriptedAgent, resolve

SCENARIOS = ("duplicate", "timeout_retry", "concurrent", "crash_before_ack")
REDELIVERY_ERROR_MODES = ("report", "fail")
_HANDLER_ERRORS = (Exception, asyncio.CancelledError)


class RedeliveryErrorWarning(UserWarning):
    """The effect happened once, but the handler raised while handling a delivery."""


@dataclass(frozen=True)
class ReplayCase:
    handler: Callable[[Any], Any]
    effects: Callable[[Any], int]
    event: Any
    key: Any


@dataclass(frozen=True)
class TrialResult:
    scenario: str
    repetition: int
    deliveries: int
    observed_effects: int
    errors: tuple[str, ...] = ()
    trace: tuple[str, ...] = ()
    fail_on_errors: bool = False
    inconclusive: str = ""             # why this trial could not test what it set out to
    max_in_flight: int | None = None   # async concurrent only: peak overlapping deliveries

    @property
    def effect_ok(self) -> bool:
        return self.observed_effects == 1

    @property
    def passed(self) -> bool:
        return (self.effect_ok and not self.inconclusive
                and not (self.fail_on_errors and self.errors))


@dataclass
class ReplayResult:
    trials: list[TrialResult] = field(default_factory=list)
    redelivery_errors: str = "report"

    @property
    def passed(self) -> bool:
        return all(trial.passed for trial in self.trials)

    @property
    def trials_with_errors(self) -> list[TrialResult]:
        return [t for t in self.trials if t.errors]

    def assert_passed(self, _stacklevel: int = 2) -> "ReplayResult":
        lines = []
        for scenario in dict.fromkeys(t.scenario for t in self.trials):
            trials = [t for t in self.trials if t.scenario == scenario]
            failed = [t for t in trials if not t.passed]
            if not failed:
                continue
            counts = sorted({t.observed_effects for t in trials})
            deliveries = sorted({t.deliveries for t in trials})
            errored = sum(bool(t.errors) for t in trials)
            reasons = []
            if any(not t.effect_ok for t in failed):
                reasons.append(f"observed effects={counts}, expected exactly 1")
            if any(t.inconclusive for t in failed):
                reasons.append("inconclusive: " + next(t.inconclusive for t in failed
                                                        if t.inconclusive))
            if self.redelivery_errors == "fail" and any(t.errors for t in failed):
                reasons.append("the handler raised (redelivery_errors='fail')")
            lines.append(
                f"{scenario}: failed {len(failed)}/{len(trials)} repetitions; "
                f"deliveries per trial={deliveries}; repetitions with handler errors={errored}; "
                + "; ".join(reasons)
            )
            for trial in failed[:5]:
                lines.append(
                    f"  repetition {trial.repetition}: deliveries={trial.deliveries}, "
                    f"observed effects={trial.observed_effects}, errors={list(trial.errors)}"
                    + (f", inconclusive={trial.inconclusive!r}" if trial.inconclusive else "")
                )
        if lines:
            raise AssertionError("replay-twice detected a failed replay drill:\n" + "\n".join(lines))
        errored = self.trials_with_errors
        if errored:
            sample = errored[0]
            warnings.warn(
                f"replay-twice: effects happened exactly once, but in {len(errored)}/"
                f"{len(self.trials)} trials the handler raised while handling a delivery "
                f"(first: {sample.scenario} {list(sample.errors)[:2]}). A webhook that errors "
                "on redelivery is usually retried again by the sender. "
                "Use redelivery_errors='fail' to fail on this.",
                RedeliveryErrorWarning, stacklevel=_stacklevel,
            )
        return self


def _positive(name: str, value: int, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _mode(value: str) -> str:
    if value not in REDELIVERY_ERROR_MODES:
        raise ValueError(f"redelivery_errors must be one of {REDELIVERY_ERROR_MODES}")
    return value


def _is_async(handler: Callable) -> bool:
    return (inspect.iscoroutinefunction(handler)
            or inspect.iscoroutinefunction(getattr(handler, "__call__", None)))


def _describe(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _count(case: ReplayCase) -> int:
    count = resolve(case.effects(case.key))
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise TypeError(f"effects(key) must return a nonnegative integer, got {count!r}")
    return count


class _Recorder:
    """Wraps the handler: counts deliveries and keeps the handler's own exceptions.

    Errors injected by the drill (lost replies, lost acks) never pass through
    here, so they are not mistaken for handler errors.
    """

    def __init__(self, handler: Callable):
        self.handler = handler
        self.calls = 0
        self.errors: list[str] = []
        self._lock = threading.Lock()

    def _record(self, exc: BaseException) -> None:
        if isinstance(exc, _HANDLER_ERRORS):
            with self._lock:
                self.errors.append(_describe(exc))

    def __call__(self, event: Any) -> Any:
        with self._lock:
            self.calls += 1
        try:
            result = self.handler(event)
        except BaseException as exc:
            self._record(exc)
            raise
        if inspect.isawaitable(result):
            return self._watch(result)
        return result

    async def _watch(self, awaitable):
        try:
            return await awaitable
        except BaseException as exc:
            self._record(exc)
            raise


class Replay:
    def __init__(self, threads: int = 8, repeats: int = 1, redelivery_errors: str = "report"):
        self.threads = _positive("threads", threads, 2)
        self.repeats = _positive("repeats", repeats)
        self.redelivery_errors = _mode(redelivery_errors)

    def measure(
        self, handler: Callable | None = None, effects: Callable | None = None,
        event: Any = None, key: Any = None, *, scenarios: Iterable[str] = ("duplicate",),
        threads: int | None = None, repeats: int | None = None,
        case_factory: Callable[[], ReplayCase] | None = None,
        redelivery_errors: str | None = None,
    ) -> ReplayResult:
        """Run the drills and return every observation without asserting or warning."""
        if isinstance(scenarios, str):
            scenarios = (scenarios,)
        names = tuple(scenarios)
        if not names or len(set(names)) != len(names) or any(n not in SCENARIOS for n in names):
            raise ValueError(f"choose distinct scenarios from {SCENARIOS}")
        worker_count = self.threads if threads is None else _positive("threads", threads, 2)
        repeat_count = self.repeats if repeats is None else _positive("repeats", repeats)
        mode = self.redelivery_errors if redelivery_errors is None else _mode(redelivery_errors)
        if case_factory is not None:
            if handler is not None or effects is not None or event is not None or key is not None:
                raise ValueError("use either case_factory or an explicit handler/effects/event/key")
        else:
            if not callable(handler) or not callable(effects):
                raise TypeError("handler and effects must be callable")
            if len(names) * repeat_count > 1:
                raise ValueError("multiple trials require a case_factory with fresh state or fresh keys")
            case_factory = lambda: ReplayCase(handler, effects, event, key)
        result = ReplayResult(redelivery_errors=mode)
        for name in names:
            for repetition in range(1, repeat_count + 1):
                case = resolve(case_factory())     # an async factory is awaited too
                if not isinstance(case, ReplayCase):
                    raise TypeError("case_factory must return ReplayCase")
                # Reject a dirty key before performing any deliveries. A factory may
                # reuse the literal key only if its underlying store is fresh.
                if _count(case) != 0:
                    raise ValueError(f"{name}: case_factory must supply an unused key or fresh store")
                result.trials.append(
                    self._trial(case, name, repetition, worker_count, mode == "fail"))
        return result

    def __call__(self, *args, **kwargs) -> ReplayResult:
        """Run the drills, raise AssertionError on failure, warn on handler errors."""
        return self.measure(*args, **kwargs).assert_passed(_stacklevel=3)

    @staticmethod
    def _concurrent(recorder: _Recorder, case: ReplayCase, threads: int) -> int | None:
        """Deliver the event `threads` times at once.

        Returns the peak number of overlapping deliveries for async handlers,
        None for threaded delivery (the barrier releases all threads together).
        """
        if _is_async(case.handler):
            # Coroutine handlers: every delivery is a task on one event loop; they
            # interleave at each await, the way an async server runs them.
            state = {"in_flight": 0, "peak": 0}

            async def one():
                state["in_flight"] += 1
                state["peak"] = max(state["peak"], state["in_flight"])
                try:
                    return await recorder(case.event)
                finally:
                    state["in_flight"] -= 1

            async def run_all():
                return await asyncio.gather(*(one() for _ in range(threads)),
                                            return_exceptions=True)

            resolve(run_all())
            return state["peak"]

        barrier = Barrier(threads)

        def worker():
            barrier.wait(timeout=10)
            try:
                resolve(recorder(case.event))
            except _HANDLER_ERRORS:
                pass   # already recorded

        with ThreadPoolExecutor(max_workers=threads) as pool:
            for future in [pool.submit(worker) for _ in range(threads)]:
                try:
                    future.result()
                except Exception as exc:          # e.g. BrokenBarrierError
                    recorder.errors.append(_describe(exc))
        return None

    @staticmethod
    def _trial(case: ReplayCase, name: str, repetition: int, threads: int,
               fail_on_errors: bool) -> TrialResult:
        recorder = _Recorder(case.handler)
        trace = ()
        peak = None

        if name == "concurrent":
            peak = Replay._concurrent(recorder, case, threads)
        elif name == "duplicate":
            for _ in range(2):
                try:
                    resolve(recorder(case.event))
                except _HANDLER_ERRORS:
                    pass
        elif name == "timeout_retry":
            agent = ScriptedAgent()
            try:
                agent.run(LoseFirstReply(recorder), case.event)
            except _HANDLER_ERRORS:
                pass
            trace = tuple(agent.trace)
        else:
            transport = LoseFirstReply(recorder, CrashBeforeAck)
            for _ in range(2):
                try:
                    transport(case.event)
                except _HANDLER_ERRORS:
                    pass

        inconclusive = ""
        if recorder.calls < 2:
            first = recorder.errors[0] if recorder.errors else "no error"
            inconclusive = (f"no redelivery happened: the first delivery raised ({first}), "
                            "so the retry under test never ran")
        elif peak is not None and peak < 2:
            inconclusive = ("concurrent deliveries did not overlap (peak 1 in flight): the "
                            "async handler never yielded to the event loop, for example "
                            "blocking I/O inside async def; run blocking work with "
                            "asyncio.to_thread, or drill the sync function")
        return TrialResult(name, repetition, recorder.calls, _count(case),
                           tuple(recorder.errors), trace, fail_on_errors, inconclusive, peak)
