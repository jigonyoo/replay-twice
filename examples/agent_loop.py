"""Run from the project root after installing the package."""
from pathlib import Path
import tempfile
from uuid import uuid4

from replay_twice import LoseFirstReply, ScriptedAgent
from replay_twice.examples import SQLiteHandlers, STRATEGIES


def main():
    with tempfile.TemporaryDirectory(prefix="replay-twice-agent-") as scratch:
        for mode in ("sync", "async"):
            for strategy in STRATEGIES:
                store = SQLiteHandlers(Path(scratch) / f"{mode}-{strategy}-{uuid4().hex}.sqlite",
                                       strategy)
                case = store.case("refund", "example-order", mode=mode)
                agent = ScriptedAgent()
                try:
                    agent.run(LoseFirstReply(case.handler), case.event)
                    outcome = "ok"
                except Exception as exc:   # guarded_raises: the retry raises
                    outcome = type(exc).__name__
                print(f"{mode:5} {strategy:15} effects={case.effects(case.key)} "
                      f"retry={outcome:14} trace={agent.trace}")


if __name__ == "__main__":
    main()
