"""SQLite task queue. A claim is one update, so a task starts once.

Isolated tasks on the same folder may run together. Only one task that
edits a folder directly may run at a time. A concurrency cap is part of
the same update. A running task whose owner is gone returns to waiting.

The claim uses SQLite ``RETURNING``, which needs SQLite 3.35 or newer.
"""

from __future__ import annotations

import contextlib
import sqlite3
import threading
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('waiting', 'running', 'finished')),
    isolated INTEGER NOT NULL CHECK (isolated IN (0, 1)),
    folder TEXT NOT NULL,
    owner TEXT
);
"""

_CLAIM = """
UPDATE tasks
SET status = 'running', owner = ?
WHERE id = (
    SELECT t.id FROM tasks AS t
    WHERE t.status = 'waiting'
      AND (
            t.isolated = 1
            OR NOT EXISTS (
                SELECT 1 FROM tasks AS other
                WHERE other.status = 'running'
                  AND other.isolated = 0
                  AND other.folder = t.folder
            )
          )
      AND (SELECT COUNT(*) FROM tasks WHERE status = 'running') < ?
    ORDER BY t.id
    LIMIT 1
)
RETURNING id, title, status, isolated, folder, owner
"""


class Scheduler:
    def __init__(self, path: str, cap: int) -> None:
        if cap < 1:
            raise ValueError("cap must be at least 1")
        self.path = path
        self.cap = cap
        self._ready = threading.Event()
        with self._open() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            conn.commit()

    def add(self, title: str, folder: str, isolated: bool) -> int:
        with self._open() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, status, isolated, folder) VALUES (?, 'waiting', ?, ?)",
                (title, 1 if isolated else 0, folder),
            )
            conn.commit()
            task_id = int(cur.lastrowid)
        self._ready.set()
        return task_id

    def claim(self, owner: str) -> Optional[dict]:
        name = (owner or "").strip()
        if not name:
            raise ValueError("owner is required")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(_CLAIM, (name, self.cap)).fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        if row is None:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "status": row[2],
            "isolated": bool(row[3]),
            "folder": row[4],
            "owner": row[5],
        }

    def finish(self, task_id: int) -> None:
        with self._open() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'finished', owner = NULL "
                "WHERE id = ? AND status = 'running'",
                (task_id,),
            )
            conn.commit()
        self._ready.set()

    def recover(self, live_owners: set[str]) -> int:
        """Return running tasks to waiting when their owner is not in ``live_owners``."""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT id, owner FROM tasks WHERE status = 'running'"
            ).fetchall()
            stale = [row[0] for row in rows if row[1] not in live_owners]
            for task_id in stale:
                conn.execute(
                    "UPDATE tasks SET status = 'waiting', owner = NULL WHERE id = ?",
                    (task_id,),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        if stale:
            self._ready.set()
        return len(stale)

    def waiting(self) -> int:
        with self._open() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = 'waiting'"
            ).fetchone()
        return int(row[0])

    def notify(self) -> None:
        self._ready.set()

    def wait_for_work(self, timeout: float) -> bool:
        """Block until ``notify``, ``add``, ``finish``, or ``recover``, or until timeout."""
        signaled = self._ready.wait(timeout)
        self._ready.clear()
        return signaled

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _open(self):
        """Connection that closes when the block exits. ``with conn`` does not."""
        return contextlib.closing(self._connect())
