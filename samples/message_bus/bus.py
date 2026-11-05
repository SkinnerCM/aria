"""Append-only message bus with signed sender names.

A privileged name is recorded only when the caller presents the token
issued for that exact name. Otherwise the message is stored as coming
from an outside caller. The signing secret never leaves this object.
"""

from __future__ import annotations

import hashlib
import hmac
import queue
import re
import secrets
import threading
from typing import Dict, List, Optional

_PRIVILEGED = re.compile(r"^(director|manager:[0-9]+|worker:[0-9]+)$")
OUTSIDER = "outsider"


def _same(left: str, right: str) -> bool:
    if len(left) != len(right):
        hmac.compare_digest(left, left)
        return False
    return hmac.compare_digest(left, right)


class MessageBus:
    def __init__(self) -> None:
        self._secret = secrets.token_bytes(32)
        self._lock = threading.Lock()
        self._log: List[Dict[str, object]] = []
        self._listeners: List[queue.Queue] = []

    def token_for(self, name: str) -> str:
        """Token for one exact name. In-process only: outside callers cannot mint one.

        The secret is not part of the result.
        """
        principal = (name or "").strip()
        if not principal:
            raise ValueError("name is required")
        return hmac.new(self._secret, principal.encode("utf-8"), hashlib.sha256).hexdigest()

    def listen(self) -> queue.Queue:
        """Queue that receives each later message. Already-stored messages are not replayed here."""
        box: queue.Queue = queue.Queue()
        with self._lock:
            self._listeners.append(box)
        return box

    def unlisten(self, box: queue.Queue) -> None:
        """Stop delivering new messages to a queue from ``listen``."""
        with self._lock:
            self._listeners = [item for item in self._listeners if item is not box]

    def publish(self, sender: str, text: str, token: str = "") -> Dict[str, object]:
        recorded = self._authorize(sender, token)
        with self._lock:
            message = {
                "id": len(self._log) + 1,
                "sender": recorded,
                "text": str(text),
            }
            self._log.append(message)
            listeners = list(self._listeners)
            stored = dict(message)
        for box in listeners:
            box.put(dict(stored))
        return stored

    def history(self, since_id: int = 0) -> List[Dict[str, object]]:
        """Messages with id greater than ``since_id``, oldest first."""
        with self._lock:
            return [dict(row) for row in self._log if int(row["id"]) > since_id]

    def _authorize(self, sender: str, token: str) -> str:
        name = (sender or "").strip()
        if not _PRIVILEGED.match(name):
            return name or OUTSIDER
        if _same(self.token_for(name), (token or "").strip()):
            return name
        return OUTSIDER
