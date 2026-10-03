"""Measured SQLite matrix, including independent runs of concurrent trials."""
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import random
import sys
import tempfile
import uuid

from . import Replay, SCENARIOS, __version__
from .examples import STRATEGIES, SQLiteHandlers

# (flow label, event kind, handler mode)
FLOWS = (("refund", "refund", "sync"),
         ("payment.succeeded webhook", "payment.succeeded", "sync"),
         ("refund (async tool)", "refund", "async"))


def build_report(output: Path, *, repeats=200, threads=8, runs=3, seed=0):
    Replay(threads=threads, repeats=repeats)  # validate before creating files
    if isinstance(runs, bool) or not isinstance(runs, int) or runs < 1:
        raise ValueError("runs must be a positive integer")
    output.mkdir(parents=True, exist_ok=True)
    session = uuid.uuid4().hex
    random_keys = random.Random(seed)
    rows = []
    # The SQLite stores are scratch state: they live in a temporary directory and
    # only the JSON and Markdown results are written to `output`.
    with tempfile.TemporaryDirectory(prefix="replay-twice-") as scratch:
        for run in range(1, runs + 1):
            for flow, kind, mode in FLOWS:
                for strategy in STRATEGIES:
                    store = SQLiteHandlers(
                        Path(scratch) / f"{session}-{run}-{kind}-{mode}-{strategy}.sqlite", strategy)
                    for scenario in SCENARIOS:
                        trial_count = repeats if scenario == "concurrent" else 1

                        def fresh_case():
                            return store.case(kind, f"{random_keys.getrandbits(128):032x}",
                                              mode=mode)

                        result = Replay(threads=threads).measure(
                            case_factory=fresh_case, scenarios=[scenario], repeats=trial_count,
                        )
                        rows.append({
                            "run": run, "flow": flow, "kind": kind, "mode": mode,
                            "handler": strategy, "scenario": scenario, "trials": trial_count,
                            "failed_trials": sum(not t.effect_ok for t in result.trials),
                            "duplicate_trials": sum(t.observed_effects > 1 for t in result.trials),
                            "error_trials": sum(bool(t.errors) for t in result.trials),
                            "effects_histogram": dict(
                                Counter(t.observed_effects for t in result.trials)),
                            "observations": [asdict(t) for t in result.trials],
                        })
    return {
        "environment": {"os": platform.platform(), "python": platform.python_version(),
                        "package_version": __version__, "seed": seed, "threads": threads,
                        "concurrent_repeats": repeats, "runs": runs, "race_delay_seconds": 0.001,
                        "utc": datetime.now(timezone.utc).isoformat()},
        "note": "Concurrency can vary across runs. Seed controls event IDs, not thread scheduling. "
                "check_then_act deliberately sleeps between reading and writing. "
                "SQLite ledger rows are simulated effects; no payment API is called.",
        "rows": rows,
    }


def _range(values):
    lo, hi = min(values), max(values)
    return f"{lo}" if lo == hi else f"{lo}–{hi}"


def markdown(data):
    env = data["environment"]
    lines = ["# replay-twice measurements", "", data["note"], "",
             f"Python {env['python']} on {env['os']}, package {env['package_version']}, "
             f"{env['threads']} threads, {env['concurrent_repeats']} concurrent trials per cell, "
             f"{env['runs']} runs, seed {env['seed']}.", "",
             "Each cell: trials with a duplicated effect / trials where the handler raised, "
             "out of the trials per run. Ranges are exact minimum–maximum across runs.", "",
             "| Flow | Handler | " + " | ".join(SCENARIOS) + " |",
             "|---|---|" + "---|" * len(SCENARIOS)]
    for flow, _, _ in FLOWS:
        for strategy in STRATEGIES:
            cells = []
            for scenario in SCENARIOS:
                rows = [r for r in data["rows"] if
                        (r["flow"], r["handler"], r["scenario"]) == (flow, strategy, scenario)]
                dup = _range([r["duplicate_trials"] for r in rows])
                err = _range([r["error_trials"] for r in rows])
                cells.append(f"dup {dup} / err {err} of {rows[0]['trials']}")
            lines.append(f"| {flow} | {strategy} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    report_parser = subparsers.add_parser("report", help="run the offline SQLite matrix")
    report_parser.add_argument("--repeats", type=int, default=200)
    report_parser.add_argument("--threads", type=int, default=8)
    report_parser.add_argument("--runs", type=int, default=3)
    report_parser.add_argument("--seed", type=int, default=0)
    report_parser.add_argument("--output", type=Path, default=Path("reports"))
    arguments = list(sys.argv[1:] if argv is None else argv)
    # Support both `replay-twice report` and `python -m replay_twice.report`.
    if not arguments or arguments[0] != "report":
        arguments.insert(0, "report")
    args = parser.parse_args(arguments)
    try:
        data = build_report(args.output, repeats=args.repeats, threads=args.threads,
                            runs=args.runs, seed=args.seed)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"report failed: {exc}\n")
    # Preserve previous measurements without deleting or replacing artifacts.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    json_path = args.output / f"report-{stamp}.json"
    md_path = args.output / f"report-{stamp}.md"
    rendered = markdown(data)
    json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    print(f"JSON: {json_path}\nMarkdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
