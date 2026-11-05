"""Competing claimers, the folder rule, the cap, and dead-owner recovery."""

from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scheduler import Scheduler


def _take_all(sched: Scheduler, owner: str, found: list, errors: list) -> None:
    try:
        while True:
            row = sched.claim(owner)
            if row is None:
                return
            found.append(row["id"])
    except Exception as exc:  # noqa: BLE001 — the check reports the thread failure
        errors.append(exc)


def main() -> None:
    with tempfile.TemporaryDirectory() as raw:
        path = str(Path(raw) / "queue.db")
        sched = Scheduler(path, cap=20)
        ids = [sched.add(f"job-{n}", "repo", isolated=True) for n in range(20)]
        found: list = []
        errors: list = []
        threads = [
            threading.Thread(target=_take_all, args=(sched, f"owner-{n}", found, errors))
            for n in range(8)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert not errors, errors
        assert sorted(found) == ids
        assert sched.claim("extra") is None

        limited = Scheduler(str(Path(raw) / "cap.db"), cap=2)
        limited.add("a", "repo", isolated=True)
        limited.add("b", "repo", isolated=True)
        limited.add("c", "repo", isolated=True)
        first = limited.claim("one")
        second = limited.claim("two")
        assert first and second and first["id"] != second["id"]
        assert limited.claim("three") is None
        limited.finish(first["id"])
        third = limited.claim("three")
        assert third is not None and third["id"] != second["id"]
        assert third["id"] != first["id"]
        limited.finish(second["id"])
        limited.finish(third["id"])
        fresh = limited.add("d", "repo", isolated=True)
        again_row = limited.claim("later")
        assert again_row is not None and again_row["id"] == fresh
        assert again_row["id"] not in {first["id"], second["id"], third["id"]}

        folders = Scheduler(str(Path(raw) / "folder.db"), cap=5)
        live_a = folders.add("edit-a", "site", isolated=False)
        live_b = folders.add("edit-b", "site", isolated=False)
        side = folders.add("side", "site", isolated=True)
        got = folders.claim("p")
        assert got["id"] == live_a and got["isolated"] is False
        got = folders.claim("q")
        assert got["id"] == side and got["isolated"] is True
        assert folders.claim("r") is None
        folders.finish(live_a)
        got = folders.claim("r")
        assert got["id"] == live_b

        dead = Scheduler(str(Path(raw) / "dead.db"), cap=2)
        task_id = dead.add("resume", "repo", isolated=True)
        assert dead.claim("gone")["id"] == task_id
        assert dead.recover(set()) == 1
        assert dead.waiting() == 1
        again = dead.claim("fresh")
        assert again["id"] == task_id and again["owner"] == "fresh"
        assert dead.recover({"fresh"}) == 0

        ping = Scheduler(str(Path(raw) / "wake.db"), cap=1)
        started = threading.Event()

        def waiter() -> None:
            started.set()
            assert ping.wait_for_work(5)

        thread = threading.Thread(target=waiter)
        thread.start()
        assert started.wait(2)
        ping.notify()
        thread.join(timeout=5)
        assert not thread.is_alive()

    print("task scheduler: ok")


if __name__ == "__main__":
    main()
