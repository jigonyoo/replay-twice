# Examples

The SQLite handlers live in the installed `replay_twice.examples` module, so `replay-twice report` also works outside a source checkout. `SQLiteHandlers(path, strategy)` takes one of `naive`, `check_then_act`, `guarded_raises` or `guarded`, and `case(kind, key, mode="sync"|"async")` returns a `ReplayCase` for a `refund` tool or a `payment.succeeded` webhook. Ledger rows stand in for the effect; nothing leaves the machine.

- `python examples/agent_loop.py` runs the scripted tool loop (call, lost reply, retry with the same arguments) against every handler, sync and async.
- `pytest -q examples/test_usage.py` runs the fixture and decorator examples.
