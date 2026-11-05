"""Signed names, live delivery, and history for a late reader."""

from __future__ import annotations

import queue
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bus import OUTSIDER, MessageBus


def main() -> None:
    bus = MessageBus()
    director = bus.token_for("director")
    worker = bus.token_for("worker:7")

    live = bus.listen()
    first = bus.publish("director", "plan", director)
    assert first["sender"] == "director"
    assert first["id"] == 1
    assert live.get(timeout=2)["text"] == "plan"

    forged = bus.publish("director", "pretend", token="")
    assert forged["sender"] == OUTSIDER
    swapped = bus.publish("director", "other-token", worker)
    assert swapped["sender"] == OUTSIDER
    assert bus.publish("manager:3", "no", director)["sender"] == OUTSIDER
    page = bus.publish("page", "hello")
    assert page["sender"] == "page"

    late = bus.history(since_id=1)
    assert [row["id"] for row in late] == [2, 3, 4, 5]
    late[0]["text"] = "changed"
    assert bus.history(since_id=1)[0]["text"] == "pretend"

    while not live.empty():
        live.get_nowait()
    bus.unlisten(live)
    bus.publish("page", "after")
    assert live.empty()

    other = MessageBus()
    assert other.publish("director", "x", director)["sender"] == OUTSIDER
    assert "\n" not in director

    print("message bus: ok")


if __name__ == "__main__":
    main()
