"""Public API for offline duplicate-delivery checks."""
import inspect
from functools import wraps

from .agent import CrashBeforeAck, LoseFirstReply, ScriptedAgent
from .core import (REDELIVERY_ERROR_MODES, SCENARIOS, RedeliveryErrorWarning, Replay,
                   ReplayCase, ReplayResult, TrialResult)

__version__ = "0.2.0"
__all__ = ["Replay", "ReplayCase", "ReplayResult", "TrialResult", "SCENARIOS",
           "REDELIVERY_ERROR_MODES", "RedeliveryErrorWarning", "replay_twice",
           "ScriptedAgent", "LoseFirstReply", "CrashBeforeAck"]

_DEFAULTS = {"threads": 8, "repeats": 1, "redelivery_errors": "report"}
_OPTIONS = {"threads": "--replay-threads", "repeats": "--replay-repeats",
            "redelivery_errors": "--replay-redelivery-errors"}


def replay_twice(*, scenarios=SCENARIOS, threads=None, repeats=None, redelivery_errors=None):
    """Decorate a pytest test that returns a fresh ReplayCase on each invocation.

    The test's own fixtures and parametrization still work. Options left as None
    take the pytest command-line value (--replay-threads, --replay-repeats,
    --replay-redelivery-errors); options given here override the command line.
    The test may be a coroutine function; it is awaited on the drill loop.
    """
    explicit = {"threads": threads, "repeats": repeats, "redelivery_errors": redelivery_errors}

    def decorate(function):
        signature = inspect.signature(function)
        wants_request = "request" in signature.parameters
        params = list(signature.parameters.values())
        if not wants_request:
            request_param = inspect.Parameter("request", inspect.Parameter.KEYWORD_ONLY)
            at = next((i for i, p in enumerate(params)
                       if p.kind is inspect.Parameter.VAR_KEYWORD), len(params))
            params.insert(at, request_param)

        @wraps(function)
        def check(*args, request=None, **kwargs):
            if wants_request:
                kwargs["request"] = request
            options = {}
            for name, value in explicit.items():
                if value is None:
                    config = getattr(request, "config", None)
                    value = (config.getoption(_OPTIONS[name], _DEFAULTS[name])
                             if config is not None else _DEFAULTS[name])
                options[name] = value
            Replay(**options)(case_factory=lambda: function(*args, **kwargs),
                              scenarios=scenarios)

        check.__signature__ = signature.replace(parameters=params)
        return check
    return decorate
