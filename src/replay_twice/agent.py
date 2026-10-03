"""A scripted tool loop, a transport that loses a successful reply, and the
event loop that async handlers run on."""
import asyncio
import inspect
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

_loop: "asyncio.AbstractEventLoop | None" = None
_loop_lock = threading.Lock()


def drill_loop() -> asyncio.AbstractEventLoop:
    """One long-lived event loop, on its own daemon thread, for every async handler.

    Reusing a single loop matters: handlers often keep loop-bound state (an
    asyncio.Lock, a cached client or pool) between calls, and a fresh loop per
    call would break them with "bound to a different event loop" errors.
    """
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_forever, name="replay-twice-loop",
                             daemon=True).start()
            _loop = loop
        return _loop


def resolve(value: Any) -> Any:
    """Run an awaitable to completion on the drill loop; pass plain values through."""
    if not inspect.isawaitable(value):
        return value
    loop = drill_loop()
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is loop:
        raise RuntimeError("replay-twice cannot block its own event loop; "
                           "do not start a drill from inside a handler")

    async def wait():
        return await value

    return asyncio.run_coroutine_threadsafe(wait(), loop).result()


class CrashBeforeAck(RuntimeError):
    """Synthetic loss of an acknowledgement; no process is killed."""


class LoseFirstReply:
    """Run the handler to completion, then hide its first successful reply.

    Async handlers are awaited before the reply is hidden, so the side effect
    has really happened when the injected error is raised.
    """

    def __init__(self, handler: Callable, error: type[Exception] = TimeoutError):
        self.handler = handler
        self.error = error
        self.lost = False
        self.deliveries = 0

    def __call__(self, event: Any) -> Any:
        self.deliveries += 1
        result = resolve(self.handler(event))
        if not self.lost:
            self.lost = True
            raise self.error("injected after handler returned; reply not delivered")
        return result


@dataclass
class ScriptedAgent:
    """Call a tool, observe a timeout, retry with the exact same arguments."""

    trace: list[str] = field(default_factory=list)

    def run(self, tool: Callable, arguments: Any) -> Any:
        self.trace.append("tool_call")
        try:
            result = resolve(tool(arguments))
        except TimeoutError:
            self.trace.extend(["timeout", "retry_same_arguments", "tool_call"])
            result = resolve(tool(arguments))
        self.trace.append("tool_result")
        return result
