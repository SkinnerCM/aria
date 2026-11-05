"""One live terminal session.

Windows opens a ConPTY through pywinpty. Every other system opens a
ptyprocess session. Bytes already produced are kept so a reader that
attaches late can stream them.
"""

from __future__ import annotations

import os
import threading
import time
from typing import List, Optional


class Session:
    def __init__(self, argv: List[str], rows: int = 24, cols: int = 80) -> None:
        if not argv:
            raise ValueError("argv is required")
        self.argv = list(argv)
        self.rows = rows
        self.cols = cols
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._closed = False
        self._thread: Optional[threading.Thread] = None
        if os.name == "nt":
            from winpty import PtyProcess
        else:
            from ptyprocess import PtyProcess
        self._child = PtyProcess.spawn(self.argv, dimensions=(self.rows, self.cols))
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()

    def read(self, timeout: float = 2.0) -> bytes:
        """Bytes captured so far. Waits up to ``timeout`` for the first byte."""
        if not self._buf and timeout:
            self._ready.wait(timeout)
        with self._lock:
            return bytes(self._buf)

    def write(self, data: bytes) -> None:
        self._child.write(data)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._child.terminate(force=True)
        except Exception:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _append(self, chunk: bytes) -> None:
        if not chunk:
            return
        with self._lock:
            self._buf.extend(chunk)
            if len(self._buf) > 65536:
                del self._buf[:-65536]
        self._ready.set()

    def _pump(self) -> None:
        while not self._closed:
            try:
                chunk = self._child.read(4096)
            except EOFError:
                break
            except Exception:
                break
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8", "replace")
            self._append(chunk)


def read_until(session: Session, marker: bytes, timeout: float = 8.0) -> bytes:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = session.read(timeout=0.2)
        if marker in data:
            return data
        time.sleep(0.05)
    return session.read(timeout=0)
