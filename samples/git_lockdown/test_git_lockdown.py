"""A real temporary repository: its own worktree, and git refuses to run."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lockdown


def _binary(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    with open(path, "rb") as handle:
        magic = handle.read(2)
    if os.name == "nt":
        return magic == b"MZ"
    return os.access(path, os.X_OK)


def find_git() -> str:
    names = ("git.exe", "git") if os.name == "nt" else ("git",)
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        for name in names:
            candidate = os.path.join(entry, name)
            if _binary(candidate):
                return candidate
    for candidate in (
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files\Git\cmd\git.exe",
        "/usr/bin/git",
        "/opt/homebrew/bin/git",
    ):
        if _binary(candidate):
            return candidate
    raise SystemExit("git binary not found")


def _run(git: str, args: list[str], env: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run([git, *args], capture_output=True, text=True, env=env)


def main() -> None:
    assert lockdown.is_git_bindir(r"C:\Program Files\Git\cmd")
    assert lockdown.is_git_bindir("/usr/libexec/git-core")
    assert lockdown.is_git_bindir(r"C:\Program Files\Git\mingw64\libexec\git-core")
    assert not lockdown.is_git_bindir(r"C:\work\digital\bin")

    git = find_git()
    parent = os.environ.copy()
    parent.pop("GIT_EXEC_PATH", None)
    parent["PATH"] = os.pathsep.join(
        entry for entry in parent.get("PATH", "").split(os.pathsep)
        if entry and "no-git" not in entry.lower()
    )

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        repo = root / "repo"
        tree = root / "tree"
        _run(git, ["init", str(repo)], parent).check_returncode()
        (repo / "note.txt").write_text("original", encoding="utf-8")
        _run(git, ["-C", str(repo), "add", "note.txt"], parent).check_returncode()
        commit = _run(
            git,
            ["-C", str(repo), "-c", "user.email=dev@example.com", "-c", "user.name=Dev", "commit", "-m", "init"],
            parent,
        )
        assert commit.returncode == 0, commit.stderr
        added = _run(git, ["-C", str(repo), "worktree", "add", "--detach", str(tree), "HEAD"], parent)
        assert added.returncode == 0, added.stderr

        common = _run(git, ["-C", str(tree), "rev-parse", "--git-common-dir"], parent)
        assert common.returncode == 0, common.stderr
        common_path = Path(common.stdout.strip())
        if not common_path.is_absolute():
            common_path = (tree / common_path).resolve()
        assert common_path == (repo / ".git").resolve()
        (tree / "note.txt").write_text("task-copy", encoding="utf-8")
        assert (repo / "note.txt").read_text(encoding="utf-8") == "original"

        before = parent.get("PATH", "")
        blocked = lockdown.prepare(parent, str(root / "stub"))
        assert parent.get("PATH", "") == before
        assert blocked["GIT_EXEC_PATH"] == str(root / "stub")
        assert blocked["PATH"].split(os.pathsep)[0] == str(root / "stub")
        assert shutil.which("git", path=blocked["PATH"])
        resolved = shutil.which("git", path=blocked["PATH"])
        assert resolved is not None and Path(resolved).parent == root / "stub"

        if os.name == "nt":
            named = subprocess.run(
                ["cmd", "/d", "/c", "git", "-C", str(tree), "status", "--porcelain"],
                capture_output=True, text=True, env=blocked,
            )
        else:
            named = subprocess.run(
                ["git", "-C", str(tree), "status", "--porcelain"],
                capture_output=True, text=True, env=blocked,
            )
        named_text = ((named.stdout or "") + (named.stderr or "")).lower()
        assert named.returncode != 0, named_text
        assert "refused" in named_text, named_text

        direct = subprocess.run(
            [git, "-C", str(tree), "submodule"],
            capture_output=True, text=True, env=blocked,
        )
        direct_text = ((direct.stdout or "") + (direct.stderr or "")).lower()
        assert direct.returncode != 0 and "not a git command" in direct_text
        clean = subprocess.run(
            [git, "-C", str(tree), "submodule"],
            capture_output=True, text=True, env=parent,
        )
        clean_text = ((clean.stdout or "") + (clean.stderr or "")).lower()
        assert "not a git command" not in clean_text

        checkout = subprocess.run(
            [git, "-C", str(tree), "checkout", "-b", "should-not"],
            capture_output=True, text=True, env=blocked,
        )
        # Built-in commands still run by full path; the lockdown is one layer, not complete isolation.
        assert checkout.returncode == 0, (checkout.stdout or "") + (checkout.stderr or "")
        _run(git, ["-C", str(repo), "branch", "-D", "should-not"], parent)

        fetched = subprocess.run(
            [git, "-C", str(tree), "fetch", str(repo)],
            capture_output=True, text=True, env=blocked,
        )
        fetch_text = ((fetched.stdout or "") + (fetched.stderr or "")).lower()
        assert fetched.returncode != 0, fetch_text
        # Windows reaches the refusing stub. macOS and Linux cannot find git-upload-pack at all.
        # Either way the fetch fails, which is what the lockdown guarantees.
        assert "refused" in fetch_text or "not found" in fetch_text, fetch_text

    print("git lockdown: ok")


if __name__ == "__main__":
    main()
