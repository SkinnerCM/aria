"""Folder listing returns directories only, and only for loopback callers."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fs_browse


def main() -> int:
    assert fs_browse.is_loopback("127.0.0.1")
    assert fs_browse.is_loopback("localhost")
    assert fs_browse.is_loopback("::1")
    assert fs_browse.is_loopback("[::1]")
    assert not fs_browse.is_loopback("10.8.0.5")
    assert not fs_browse.is_loopback("evil.example")
    assert not fs_browse.is_loopback("testclient")

    assert fs_browse.loopback_allowed("127.0.0.1", "127.0.0.1", None)
    assert fs_browse.loopback_allowed("::1", "[::1]:8810", "http://[::1]:8810")
    assert not fs_browse.loopback_allowed("10.8.0.5", "127.0.0.1", None)
    assert not fs_browse.loopback_allowed("127.0.0.1", "evil.example", None)
    assert not fs_browse.loopback_allowed("127.0.0.1", "127.0.0.1", "https://evil.example")
    assert not fs_browse.loopback_allowed("127.0.0.1", "127.0.0.1", "null")
    assert not fs_browse.loopback_allowed("127.0.0.1", "", None)

    with tempfile.TemporaryDirectory() as raw:
        browse = Path(raw)
        alpha = browse / "alpha"
        beta = browse / "beta"
        alpha.mkdir()
        beta.mkdir()
        planted = browse / "note.txt"
        planted.write_text("not-a-folder", encoding="utf-8")

        listed = fs_browse.list_dirs(str(browse))
        names = {row["name"] for row in listed["dirs"]}
        blob = str(listed)
        assert names == {"alpha", "beta"}
        assert "note.txt" not in blob
        assert "not-a-folder" not in blob
        assert listed["parent"] == str(browse.resolve().parent)

        blocked = browse / "locked"
        blocked.mkdir()
        original = Path.is_dir

        def unreadable(path: Path) -> bool:
            if path.name == blocked.name:
                raise PermissionError("simulated unreadable directory entry")
            return original(path)

        try:
            Path.is_dir = unreadable
            skipped = {row["name"] for row in fs_browse.list_dirs(str(browse))["dirs"]}
        finally:
            Path.is_dir = original
        assert "locked" not in skipped
        assert skipped == {"alpha", "beta"}

        try:
            fs_browse.list_dirs(str(browse / "missing"))
        except ValueError:
            pass
        else:
            raise AssertionError("a missing path should fail")

        try:
            fs_browse.list_dirs(str(planted))
        except ValueError:
            pass
        else:
            raise AssertionError("a file path should fail")

    home = fs_browse.list_dirs("")
    assert home["path"]
    assert isinstance(home["dirs"], list)
    assert isinstance(home["roots"], list)

    print("folder picker: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
