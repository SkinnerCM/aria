"""Single use, expiry, a wrong code, and no approval code in the picture."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pairing import Desk, PairError


def main() -> None:
    now = {"t": 1000.0}
    desk = Desk(clock=lambda: now["t"], attempts=3)
    invite = desk.start(ttl=50)
    assert invite["qr"] == invite["invite_id"]
    assert invite["code"] not in invite["qr"]
    assert invite["code"] not in invite["invite_id"]

    granted = desk.accept(invite["invite_id"], invite["code"])
    secret = granted["secret"]
    assert secret != invite["code"]
    assert secret != invite["invite_id"]
    assert granted["session_id"] not in invite["qr"]
    assert desk.allowed(granted["session_id"], secret)
    assert not desk.allowed(granted["session_id"], "nope")
    assert not desk.allowed("missing", secret)
    try:
        desk.accept(invite["invite_id"], invite["code"])
        raise AssertionError("invitation worked twice")
    except PairError as exc:
        assert str(exc) == "invitation was not accepted"

    fresh = desk.start(ttl=10)
    now["t"] += 11
    try:
        desk.accept(fresh["invite_id"], fresh["code"])
        raise AssertionError("expired invitation worked")
    except PairError as exc:
        assert str(exc) == "invitation was not accepted"

    retry = desk.start(ttl=30)
    for _ in range(3):
        try:
            desk.accept(retry["invite_id"], "00000000")
        except PairError as exc:
            assert str(exc) == "invitation was not accepted"
        else:
            raise AssertionError("wrong code was accepted")
    try:
        desk.accept(retry["invite_id"], retry["code"])
    except PairError:
        pass
    else:
        raise AssertionError("code still worked after the attempt limit")

    missing = "invitation was not accepted"
    try:
        desk.accept("missing", "00000000")
    except PairError as exc:
        assert str(exc) == missing

    print("phone pairing: ok")


if __name__ == "__main__":
    main()
