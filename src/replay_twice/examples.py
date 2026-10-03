"""SQLite demo handlers. Only a ledger row represents a simulated effect."""
import asyncio
from pathlib import Path
import sqlite3
import time

# naive           always applies the effect
# check_then_act  reads first, then writes (sequential duplicates blocked, races under overlap)
# guarded_raises  unique claim in the same transaction, but a duplicate raises IntegrityError
#                 (the effect happens once; the sender sees an error and retries again)
# guarded         unique claim with INSERT OR IGNORE; a duplicate returns "already_applied"
STRATEGIES = ("naive", "check_then_act", "guarded_raises", "guarded")
KINDS = ("refund", "payment.succeeded")
MODES = ("sync", "async")


class SQLiteHandlers:
    def __init__(self, database: str | Path, strategy: str, *, race_delay: float = 0.001):
        if strategy not in STRATEGIES:
            raise ValueError(f"unknown strategy: {strategy}")
        self.database = str(database)
        self.strategy = strategy
        self.race_delay = race_delay
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS claims (
                    kind TEXT NOT NULL, effect_key TEXT NOT NULL,
                    PRIMARY KEY (kind, effect_key)
                );
                CREATE TABLE IF NOT EXISTS ledger (
                    kind TEXT NOT NULL, effect_key TEXT NOT NULL,
                    amount INTEGER NOT NULL
                );
            """)
        finally:
            connection.close()

    def _connect(self):
        # Python's connection context manager does not close the connection.
        # Calls use try/finally below; initialization explicitly closes too.
        return sqlite3.connect(self.database, timeout=30)

    def _execute(self, kind: str, key: str, amount: int):
        connection = self._connect()
        try:
            if self.strategy == "check_then_act":
                found = connection.execute(
                    "SELECT 1 FROM ledger WHERE kind=? AND effect_key=? LIMIT 1", (kind, key)
                ).fetchone()
                if found:
                    return "already_applied"
                # Artificially widen a real read/write race; no barrier here.
                time.sleep(self.race_delay)
            if self.strategy == "guarded_raises":
                with connection:
                    connection.execute("INSERT INTO claims VALUES (?, ?)", (kind, key))
                    connection.execute("INSERT INTO ledger VALUES (?, ?, ?)", (kind, key, amount))
                return "applied"
            if self.strategy == "guarded":
                with connection:
                    claimed = connection.execute(
                        "INSERT OR IGNORE INTO claims VALUES (?, ?)", (kind, key)
                    ).rowcount
                    if not claimed:
                        return "already_applied"
                    connection.execute("INSERT INTO ledger VALUES (?, ?, ?)", (kind, key, amount))
                return "applied"
            with connection:
                connection.execute("INSERT INTO ledger VALUES (?, ?, ?)", (kind, key, amount))
            return "applied"
        finally:
            connection.close()

    def refund(self, order_id: str, amount: int):
        return self._execute("refund", order_id, amount)

    def refund_event(self, event):
        return self.refund(event["order_id"], event["amount"])

    def payment_succeeded(self, event):
        if event["type"] != "payment.succeeded":
            raise ValueError("expected payment.succeeded")
        return self._execute("payment.succeeded", event["id"], event["amount"])

    def effects(self, kind: str, key: str) -> int:
        connection = self._connect()
        try:
            return connection.execute(
                "SELECT COUNT(*) FROM ledger WHERE kind=? AND effect_key=?", (kind, key)
            ).fetchone()[0]
        finally:
            connection.close()

    # Async variants: the same logic behind `async def`, the way an async web
    # framework or agent toolkit would call it. The blocking SQLite work runs in a
    # worker thread, so concurrent deliveries really overlap.
    async def refund_event_async(self, event):
        return await asyncio.to_thread(self.refund_event, event)

    async def payment_succeeded_async(self, event):
        return await asyncio.to_thread(self.payment_succeeded, event)

    def case(self, kind: str, key: str, amount: int = 800, mode: str = "sync"):
        from .core import ReplayCase
        if mode not in MODES:
            raise ValueError(f"unknown mode: {mode}")
        if kind == "refund":
            event = {"order_id": key, "amount": amount}
            handler = self.refund_event_async if mode == "async" else self.refund_event
        elif kind == "payment.succeeded":
            event = {"id": key, "type": kind, "amount": amount}
            handler = (self.payment_succeeded_async if mode == "async"
                       else self.payment_succeeded)
        else:
            raise ValueError(f"unknown kind: {kind}")
        return ReplayCase(handler, lambda k: self.effects(kind, k), event, key)
