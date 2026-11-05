"""One-time invitation for a second screen.

The QR code carries only the invitation id. The short code is shown on
the desktop screen, and the person types that code into the phone. It
is not part of the QR code. Accepting the invitation once returns a new
session id and a session secret. Only the hash of the secret is kept.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from typing import Callable, Dict, Optional

_DUMMY = hashlib.sha256(b"pairing-dummy").hexdigest()


class PairError(Exception):
    """The invitation was not accepted. The message does not say why."""


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _same(stored: str, presented: str) -> bool:
    actual = _digest(presented)
    if len(stored) != len(actual):
        hmac.compare_digest(actual, actual)
        return False
    return hmac.compare_digest(stored, actual)


class Desk:
    def __init__(self, clock: Callable[[], float] = time.monotonic, attempts: int = 4) -> None:
        self._clock = clock
        self._attempts = attempts
        self._lock = threading.Lock()
        self._invites: Dict[str, dict] = {}
        self._sessions: Dict[str, str] = {}

    def start(self, ttl: float = 180.0) -> dict:
        invite_id = secrets.token_urlsafe(18)
        code = secrets.token_hex(4)
        now = self._clock()
        with self._lock:
            stale = [
                key for key, row in self._invites.items()
                if row["used"] or now >= row["expires"]
            ]
            for key in stale:
                del self._invites[key]
            self._invites[invite_id] = {
                "code": _digest(code),
                "expires": now + ttl,
                "left": self._attempts,
                "used": False,
            }
        return {"invite_id": invite_id, "code": code, "qr": invite_id}

    def accept(self, invite_id: str, code: str) -> dict:
        with self._lock:
            row = self._invites.get(invite_id)
            if row is None or row["used"] or row["left"] <= 0 or self._clock() >= row["expires"]:
                _same(_DUMMY, code or "")
                raise PairError("invitation was not accepted")
            if not _same(row["code"], code or ""):
                row["left"] -= 1
                raise PairError("invitation was not accepted")
            row["used"] = True
            secret = secrets.token_urlsafe(32)
            session_id = secrets.token_urlsafe(12)
            self._sessions[session_id] = _digest(secret)
        return {"session_id": session_id, "secret": secret}

    def allowed(self, session_id: str, secret: str) -> bool:
        with self._lock:
            stored = self._sessions.get(session_id)
        if not stored:
            _same(_DUMMY, secret or "")
            return False
        return _same(stored, secret or "")
