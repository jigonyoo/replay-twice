# replay-twice

A webhook handler or an AI agent's tool can commit a side effect and then lose its reply. The sender retries, and the same refund happens twice. Reading before writing does not help when two deliveries overlap.

replay-twice is a pytest plugin and small library that delivers the same event again, in four ways, and asks your own `effects(key)` observer whether the effect happened exactly once. It finds the problem; it does not add idempotency to your code.

- Works offline. No model, API key or network.
- Sync and `async def` handlers.
- Python 3.10+. The only runtime dependency is pytest.

## Quick start

```bash
pip install "replay-twice @ git+https://github.com/jigonyoo/replay-twice"
```

Give it the handler, an observer that counts committed effects for a key, the event, and its key. The `replay` fixture is registered automatically:

```python
from uuid import uuid4
from replay_twice import ReplayCase, SCENARIOS

def test_refund_happens_once(replay, db):
    def fresh_case():
        order_id = uuid4().hex                    # a fresh key for every trial
        return ReplayCase(
            handler=refund_tool,                  # handler(event); may be async
            effects=lambda key: db.count_refunds(key),
            event={"order_id": order_id, "amount": 800},
            key=order_id,
        )
    replay(case_factory=fresh_case, scenarios=SCENARIOS)
```

Or as a decorator on a test that returns a fresh `ReplayCase`:

```python
from replay_twice import replay_twice, SCENARIOS

@replay_twice(scenarios=SCENARIOS, redelivery_errors="fail")
def test_payment_webhook(tmp_path):
    return make_case(tmp_path)
```

A failure names the scenario, the deliveries, the effects observed and how many repetitions failed. `replay.measure(...)` returns the observations without asserting or warning, if you want to inspect them yourself.

A trial also fails as **inconclusive** when it could not test what it set out to: if the first delivery raised and nothing was redelivered, or if an `async` handler's concurrent deliveries never overlapped because it never yielded to the event loop (blocking I/O inside `async def`).

## Async handlers

`async def` handlers, async callable objects, `functools.partial` of either, and plain functions that return a coroutine are all awaited. They run on one long-lived event loop on a background thread, so loop-bound state (an `asyncio.Lock`, a cached client or connection pool) keeps working across deliveries and trials. Objects bound to your own test's event loop cannot be shared with that loop; create them inside the handler, or drill from a regular (sync) test. Async `effects` observers and async case factories, including `async def` tests under the decorator, are awaited too.

## The four scenarios

| Scenario | What happens |
|---|---|
| `duplicate` | the same event is delivered twice, one after the other |
| `timeout_retry` | the handler finishes, the reply is replaced by `TimeoutError`, and a scripted agent retries the same tool call with the same arguments |
| `crash_before_ack` | the handler finishes, an exception stands in for the lost acknowledgement, and the event is redelivered (no agent, no timeout: the queue or webhook sender's view) |
| `concurrent` | N deliveries at once: threads released together by a barrier, or, for `async def` handlers, N tasks on one event loop that interleave at every `await` (the peak overlap is recorded; no overlap makes the trial inconclusive) |

## Errors on redelivery

A handler can apply the effect once and still be wrong: if it raises on every redelivery (a unique-constraint violation that becomes a 500), the sender keeps retrying. The verdict is the effect count, and `redelivery_errors` decides what a handler exception means:

- `"report"` (default): the drill passes if the effect happened once, and emits a `RedeliveryErrorWarning` naming the scenario and the error.
- `"fail"`: any handler exception during the drill fails it.

Set it per test (`Replay(redelivery_errors="fail")`, `@replay_twice(redelivery_errors="fail")`) or for the run: `pytest --replay-redelivery-errors=fail`. Other run options: `--replay-threads` (default 8) and `--replay-repeats` (default 1). The command-line options apply to the `replay` fixture and to decorated tests; an option given explicitly in the decorator wins.

## Measured on the bundled examples

`replay_twice.examples` has SQLite implementations of a `refund` tool and a `payment.succeeded` webhook, each with four handlers, plus `async` versions:

- `naive` applies the effect every time.
- `check_then_act` reads first and writes if nothing is there; it widens the read-write gap with a 1 ms sleep.
- `guarded_raises` claims the key under a unique constraint in the same transaction, but lets the duplicate raise.
- `guarded` claims the key with `INSERT OR IGNORE` and returns "already applied".

Each cell: trials with a duplicated effect / trials where the handler raised, out of the trials per run. 8 threads, 200 concurrent trials per cell, 3 runs, seed 0; ranges would show as min–max.

| Flow | Handler | duplicate | timeout_retry | concurrent | crash_before_ack |
|---|---|---|---|---|---|
| refund | naive | dup 1 / err 0 of 1 | dup 1 / err 0 of 1 | dup 200 / err 0 of 200 | dup 1 / err 0 of 1 |
| refund | check_then_act | dup 0 / err 0 of 1 | dup 0 / err 0 of 1 | dup 200 / err 0 of 200 | dup 0 / err 0 of 1 |
| refund | guarded_raises | dup 0 / err 1 of 1 | dup 0 / err 1 of 1 | dup 0 / err 200 of 200 | dup 0 / err 1 of 1 |
| refund | guarded | dup 0 / err 0 of 1 | dup 0 / err 0 of 1 | dup 0 / err 0 of 200 | dup 0 / err 0 of 1 |
| payment.succeeded webhook | naive | dup 1 / err 0 of 1 | dup 1 / err 0 of 1 | dup 200 / err 0 of 200 | dup 1 / err 0 of 1 |
| payment.succeeded webhook | check_then_act | dup 0 / err 0 of 1 | dup 0 / err 0 of 1 | dup 200 / err 0 of 200 | dup 0 / err 0 of 1 |
| payment.succeeded webhook | guarded_raises | dup 0 / err 1 of 1 | dup 0 / err 1 of 1 | dup 0 / err 200 of 200 | dup 0 / err 1 of 1 |
| payment.succeeded webhook | guarded | dup 0 / err 0 of 1 | dup 0 / err 0 of 1 | dup 0 / err 0 of 200 | dup 0 / err 0 of 1 |
| refund (async tool) | naive | dup 1 / err 0 of 1 | dup 1 / err 0 of 1 | dup 200 / err 0 of 200 | dup 1 / err 0 of 1 |
| refund (async tool) | check_then_act | dup 0 / err 0 of 1 | dup 0 / err 0 of 1 | dup 200 / err 0 of 200 | dup 0 / err 0 of 1 |
| refund (async tool) | guarded_raises | dup 0 / err 1 of 1 | dup 0 / err 1 of 1 | dup 0 / err 200 of 200 | dup 0 / err 1 of 1 |
| refund (async tool) | guarded | dup 0 / err 0 of 1 | dup 0 / err 0 of 1 | dup 0 / err 0 of 200 | dup 0 / err 0 of 1 |

Reproduce with `replay-twice report` (about 4 minutes). Measured with replay-twice 0.2.0 on Linux, Python 3.11.15. A smaller run (50 concurrent trials, 1 run) on Python 3.10.12, in a Linux VM on the author's Mac, gave the same pattern; both logs are in [evidence/v0.2.0/](evidence/v0.2.0/), and CI runs the tests on Ubuntu and macOS. The `check_then_act` race is widened on purpose, so these counts are not a production failure rate. Concurrency can vary from run to run; the seed fixes the event IDs, not the thread schedule.

## What it cannot catch

- Several processes or servers, distributed locks, broker delivery policies, network partitions, crashes and power loss.
- Isolation behaviour of your real database. The bundled examples are SQLite.
- Duplicates on the payment provider's side, effects committed after the handler returns, or effects your observer cannot see.
- Wrong or changing keys, partial refunds that need distinct identities, payload mismatches under a reused key.
- Every possible schedule. A pass is evidence for the schedules that ran, not a proof. A handler that never returns stalls the drill; use your test runner's timeout.

Run it against an isolated test store: the handler is really invoked.

## Development

```bash
pip install -e .
pytest -q
python examples/agent_loop.py      # the scripted tool loop, sync and async
```

## License

MIT. See [LICENSE](LICENSE).

Built with AI assistance and reviewed independently twice (see STATUS_REPORT.md); the numbers above come from `replay-twice report` (raw observations: `reports/report-20261003T150804654663Z.json`).

---

Want this run against your real refund, charge or webhook flow? Fixed-scope duplicate side-effect diagnostic, from $800: [jigonyoo.com](https://jigonyoo.com)
