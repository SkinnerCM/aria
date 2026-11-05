"""Give one task its own worktree, and a worker environment that cannot run git.

The parent environment is copied, not changed. Git's directories are taken
off PATH, a refusing program is placed first, and GIT_EXEC_PATH points at
that program so git cannot load its helper programs. Built-in commands can still run if git is called by its full path.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Mapping

_TAILS = (
    ("git", "cmd"),
    ("git", "bin"),
    ("git", "mingw64", "bin"),
    ("git", "usr", "bin"),
    ("git", "mingw64", "libexec", "git-core"),
    ("git", "libexec", "git-core"),
    ("libexec", "git-core"),
)
_MESSAGE = "git is refused in this worktree. Version control stays with the parent."


def is_git_bindir(entry: str) -> bool:
    """True when ``entry`` is a Git install directory, not a name that merely contains git."""
    if not entry:
        return False
    parts = tuple(piece.lower() for piece in entry.replace("\\", "/").split("/") if piece)
    for tail in _TAILS:
        if len(parts) >= len(tail) and parts[-len(tail):] == tail:
            return True
    return False


def _real_binary(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "rb") as handle:
            magic = handle.read(2)
    except OSError:
        return False
    if os.name == "nt":
        return magic == b"MZ"
    return magic != b"#!" and os.access(path, os.X_OK)


def _holds_git(entry: str) -> bool:
    if is_git_bindir(entry):
        return True
    names = ("git.exe", "git") if os.name == "nt" else ("git",)
    return any(_real_binary(os.path.join(entry, name)) for name in names)


def write_stub(directory: str) -> str:
    """Write the refusing git program. Returns the directory."""
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    script = f"#!/bin/sh\nprintf '%s\\n' \"{_MESSAGE}\" >&2\nexit 1\n"
    git_unix = root / "git"
    git_unix.write_text(script, encoding="utf-8", newline="\n")
    try:
        git_unix.chmod(git_unix.stat().st_mode | stat.S_IEXEC)
    except OSError:
        pass
    cmd = f"@echo off\r\necho {_MESSAGE}\r\nexit /b 1\r\n"
    (root / "git.cmd").write_text(cmd, encoding="utf-8", newline="")
    (root / "git.bat").write_text(cmd, encoding="utf-8", newline="")
    return str(root)


def prepare(base: Mapping[str, str], stub_dir: str) -> dict[str, str]:
    """Return the worker environment. ``base`` is not modified."""
    bindir = write_stub(stub_dir)
    out = dict(base)
    kept = [entry for entry in (out.get("PATH") or "").split(os.pathsep) if entry and not _holds_git(entry)]
    out["PATH"] = bindir + (os.pathsep + os.pathsep.join(kept) if kept else "")
    out["GIT_EXEC_PATH"] = bindir
    return out
