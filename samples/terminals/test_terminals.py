"""Spawn a short command and read its output back from the session."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from session import Session, read_until


def main() -> None:
    argv = [sys.executable, "-c", "print('marker-sample-ok')"]
    session = Session(argv)
    try:
        data = read_until(session, b"marker-sample-ok")
    finally:
        session.close()
    assert b"marker-sample-ok" in data, data
    print("terminals: ok")


if __name__ == "__main__":
    main()
