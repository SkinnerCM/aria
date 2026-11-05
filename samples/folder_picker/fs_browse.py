"""Loopback-only folder listing for a folder picker.

The listing is directory names and paths. It never returns file names or
file contents. Peer IP, Host, and Origin must all be loopback.
"""

from __future__ import annotations

import os
import string
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse, urlsplit


def is_loopback(host: Optional[str]) -> bool:
    """Hostname or IP is loopback. A test-client name is not loopback."""
    h = (host or "").split("%")[0].strip().strip("[]").lower()
    if h.count(":") == 1 and not h.startswith("::"):
        h = h.split(":", 1)[0]
    return h in {"127.0.0.1", "::1", "localhost"}


def _hostname(host: Optional[str]) -> str:
    """Hostname from a Host header, peer address, or Origin host.

    ``urlsplit`` keeps the port on ``[::1]:8810`` from sticking to the
    name. An unbracketed peer such as ``::1`` is not a URL host, so that
    form falls back to the raw address.
    """
    text = (host or "").strip()
    if not text:
        return ""
    if text.startswith("["):
        end = text.find("]")
        if end != -1:
            inside = text[1:end].split("%", 1)[0]
            text = "[" + inside + "]" + text[end + 1:]
    else:
        text = text.split("%", 1)[0].strip()
    try:
        name = urlsplit("//" + text).hostname
    except ValueError:
        name = None
    if name:
        return name.lower()
    bare = text.strip("[]")
    if bare.count(":") == 1 and not bare.startswith("::"):
        bare = bare.split(":", 1)[0]
    return bare.lower()


def loopback_allowed(peer: Optional[str], host: Optional[str], origin: Optional[str]) -> bool:
    """True only when the peer, Host header, and Origin (if sent) are loopback."""
    if not is_loopback(_hostname(peer)):
        return False
    host_name = _hostname(host)
    if not host_name or not is_loopback(host_name):
        return False
    sent = (origin or "").strip()
    if not sent:
        return True
    if sent.lower() == "null":
        return False
    parsed = urlparse(sent)
    return is_loopback(_hostname(parsed.hostname))


def _drive_roots() -> List[dict]:
    rows: List[dict] = []
    if os.name == "nt":
        for letter in string.ascii_uppercase:
            root = Path(f"{letter}:\\")
            if root.exists():
                rows.append({"name": f"{letter}:\\", "path": str(root)})
        return rows
    rows.append({"name": "/", "path": "/"})
    return rows


def _child_dirs(path: Path) -> List[dict]:
    try:
        entries = list(path.iterdir())
    except OSError:
        raise ValueError("folder is not readable") from None
    rows: List[dict] = []
    for entry in entries:
        try:
            if entry.is_dir():
                rows.append({"name": entry.name, "path": str(entry)})
        except OSError:
            continue
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def list_dirs(path: Optional[str]) -> dict:
    """List child folders of ``path``. An empty path starts at the home folder."""
    raw = (path or "").strip()
    roots = _drive_roots()
    if not raw:
        home = Path.home()
        parent = None if home.parent == home else str(home.parent)
        try:
            dirs = _child_dirs(home)
        except ValueError:
            dirs = []
        return {"path": str(home), "parent": parent, "dirs": dirs, "roots": roots}
    try:
        folder = Path(raw).expanduser().resolve()
    except OSError:
        raise ValueError("folder was not found") from None
    if not folder.exists():
        raise ValueError("folder was not found")
    if not folder.is_dir():
        raise ValueError("path is not a folder")
    parent = None if folder.parent == folder else str(folder.parent)
    return {
        "path": str(folder),
        "parent": parent,
        "dirs": _child_dirs(folder),
        "roots": roots,
    }
