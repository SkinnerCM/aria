"""The worker interface reports a missing program, and it does not keep secrets."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncio
import sys

import base


class Present(base.CodingBackend):
    name = "present"
    label = "Present"
    install_hint = "already here"

    @property
    def bin(self) -> str:
        return sys.executable


class Missing(base.CodingBackend):
    name = "missing"
    label = "Missing"
    install_hint = "install the missing program"

    @property
    def bin(self) -> str:
        return "aria-worker-missing-bin"


class NoLogin(Present):
    def auth_status(self) -> dict:
        return {"ok": False, "detail": "no credential file", "hint": "log in"}


def main() -> int:
    missing = Missing().probe()
    assert missing["available"] is False
    assert missing["reason"] == "missing_binary"
    assert missing["hint"] == "install the missing program"

    present = Present().probe()
    assert present["available"] is True
    assert present["path"]
    assert present["reason"] == ""

    status = asyncio.run(NoLogin().status())
    assert status["available"] is True
    assert status["auth"] is False
    assert status["ready"] is False
    assert "no credential file" in status["auth_detail"]

    counted = base.usage_from_payload({
        "usage": {"input_tokens": 3, "output_tokens": "nope"},
        "total_cost_usd": 0.5,
    })
    assert counted == {"input_tokens": 3.0, "total_cost_usd": 0.5}

    try:
        asyncio.run(base.CodingBackend().run("edit the readme", "."))
    except NotImplementedError:
        pass
    else:
        raise AssertionError("the base worker must not edit files")

    print("worker interface: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
