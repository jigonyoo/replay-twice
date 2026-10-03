# STATUS_REPORT — replay-twice 0.2.0 (2026-10-04)

0.1.0 was built separately (its report is kept in `evidence/v0.1.0/`). 0.2.0 fixes two independent reviews.

## Review 1 (Claude, REVIEW_claude_20261003) → fixed
- Handler errors on redelivery did not count. → `redelivery_errors="report"|"fail"` (Replay, measure, decorator, `--replay-redelivery-errors`); report mode warns with `RedeliveryErrorWarning`; report matrix shows trials with handler errors; new example handler `guarded_raises`.
- Async handlers were never awaited (0 effects, no error). → awaited; async examples and a measured async flow.
- README had local absolute paths and full install logs. → rewritten; evidence paths scrubbed; old logs moved to `evidence/v0.1.0/`.
- Minor: SQLite scratch stores now in a temp dir; crash_before_ack vs timeout_retry explained; CI workflow (Ubuntu + macOS, Python 3.10 and 3.12).

## Review 2 (independent agent, on the review-1 fixes) → fixed
- Blocking: a new event loop per async call broke loop-bound handler state (asyncio.Lock, cached clients). → one long-lived drill loop on a background thread. Tests: `test_loop_bound_state_survives_many_trials_and_scenarios`, `test_cached_loop_client_is_not_closed_between_calls`.
- `timeout_retry` passed after a single delivery when the handler raised after committing. → any trial with fewer than 2 deliveries is inconclusive (fails). Test: `test_first_delivery_error_after_commit_is_inconclusive_not_a_pass`.
- CLI options did not reach the decorator. → decorator options default to the pytest command line; explicit values win. Tests: `test_cli_options_reach_the_decorator`, `test_decorator_keeps_fixtures_parametrize_and_request`.
- Async `concurrent` silently ran sequentially for handlers that never yield. → peak overlap recorded; no overlap = inconclusive. Tests: `test_blocking_async_handler_is_inconclusive_for_concurrent`, `test_yielding_async_handler_reports_real_overlap`.
- Minor: injected errors no longer reported as handler errors (handler wrapped by a recorder); CancelledError recorded; async case factories and async tests awaited; observer returning None is a TypeError; warning points at the calling test; no warning when the effect check fails; tmp_path retention back to pytest defaults; README documents `measure()` and the drill loop.

## Results
- Linux, Python 3.11.15: `pytest -q` → `60 passed`; `replay-twice report` (200 concurrent trials × 3 runs) → table in README, log `evidence/v0.2.0/py311-linux-cloud.txt`. Suite run 6 times in a row, no flakes.
- Linux VM on the author's Mac, Python 3.10.12: `pytest -q` → `60 passed`; report with 50 trials × 1 run → same pattern, log `evidence/v0.2.0/py310-cowork-vm-on-mac.txt`.
- macOS itself is covered by the CI matrix once the repository is on GitHub.
