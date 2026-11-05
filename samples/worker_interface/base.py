"""Interface for a pluggable code-editing worker.

A worker is an external program that edits files in one directory.
Before it is started, two facts are settled: the program is installed,
and it already has credentials. A missing login must not turn into a
question that nobody is present to answer.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

EventSink = Callable[[str, str], None]

VERSION_TIMEOUT = 20

_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "total_cost_usd",
)


def _usage_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def usage_from_payload(data: Any) -> Dict[str, float]:
    """Token and dollar fields from a JSON result. Strings are dropped."""
    if not isinstance(data, dict):
        return {}
    out: Dict[str, float] = {}
    usage = data.get("usage")
    if isinstance(usage, dict):
        for key in _USAGE_KEYS:
            if key == "total_cost_usd":
                continue
            number = _usage_number(usage.get(key))
            if number is not None:
                out[key] = number
    cost = _usage_number(data.get("total_cost_usd"))
    if cost is not None:
        out["total_cost_usd"] = cost
    return out


def format_usage(usage: Dict[str, float]) -> str:
    return " ".join(f"{key}={usage[key]}" for key in _USAGE_KEYS if key in usage)


@dataclass
class BackendResult:
    ok: bool
    summary: str = ""
    output: str = ""
    error: str = ""
    usage: Dict[str, float] = field(default_factory=dict)
    tool_names: List[str] = field(default_factory=list)


class CodingBackend:
    name = "base"
    label = "Backend"
    install_hint = ""

    @property
    def bin(self) -> str:
        """Executable name or path. Read at call time, not at import time."""
        raise NotImplementedError

    def preferred_bin_dirs(self) -> List[str]:
        """Directories searched before PATH. Empty means ordinary lookup."""
        return []

    def resolved_bin(self) -> Optional[str]:
        """Where this program lives, or None if it is not installed."""
        for directory in self.preferred_bin_dirs():
            found = shutil.which(self.bin, path=directory)
            if found:
                return found
        return shutil.which(self.bin)

    def argv(self, args: Sequence[str]) -> List[str]:
        """Command line. argv[0] is a real file when one can be found."""
        return [self.resolved_bin() or self.bin, *args]

    def auth_status(self) -> dict:
        """``{ok, detail, hint}``. ``detail`` never includes the credential."""
        return {"ok": True, "detail": "", "hint": ""}

    def probe(self) -> dict:
        """Whether ``--version`` succeeds.

        ``reason`` is ``missing_binary`` or ``probe_failed``, so a caller
        can tell "install it" from "it is installed but broken".
        """
        path = self.resolved_bin()
        if not path:
            return {"available": False, "version": "", "path": "",
                    "reason": "missing_binary",
                    "error": f"{self.bin} was not found",
                    "hint": self.install_hint}
        try:
            proc = subprocess.run([path, "--version"], capture_output=True,
                                  text=True, timeout=VERSION_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as exc:
            return {"available": False, "version": "", "path": path,
                    "reason": "probe_failed",
                    "error": f"{path} --version failed: {exc}",
                    "hint": self.install_hint}
        out = (proc.stdout or proc.stderr or "").strip()
        if proc.returncode != 0:
            return {"available": False, "version": "", "path": path,
                    "reason": "probe_failed",
                    "error": f"{path} --version exited {proc.returncode}: {out[:200]}",
                    "hint": self.install_hint}
        return {"available": True, "version": out[:200], "path": path,
                "reason": "", "error": "", "hint": ""}

    async def available(self) -> dict:
        return await asyncio.to_thread(self.probe)

    async def status(self) -> dict:
        """Install check plus credentials. Both have to hold before work starts."""
        probe = await self.available()
        auth = await asyncio.to_thread(self.auth_status)
        return {**probe, "label": self.label, "bin": self.bin,
                "auth": bool(auth.get("ok")), "auth_detail": auth.get("detail", ""),
                "auth_hint": auth.get("hint", ""),
                "ready": bool(probe.get("available")) and bool(auth.get("ok"))}

    async def run(self, task_prompt: str, work_dir: str,
                  on_event: Optional[EventSink] = None,
                  env: Optional[Dict[str, str]] = None) -> BackendResult:
        """Edit files in work_dir. Must not push or merge."""
        raise NotImplementedError
