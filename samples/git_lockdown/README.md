# Worker git lockdown

In Aria, every coding task gets its own git worktree, and all of those worktrees share the project's single `.git` directory. A worker that ran git commands of its own could therefore change the main project, not just its own copy. Telling an AI worker not to run git is not reliable, so Aria takes git away from the worker's environment instead.

## What it demonstrates

- **One worktree per task.** The test creates a real repository and a task worktree, and confirms that a change in the worktree does not touch the main copy.
- **A rebuilt worker environment.** The worker gets a copy of the parent's environment in which:
  - every git installation directory is removed from `PATH`,
  - a small stand-in `git` program that always refuses to run is placed first on `PATH`, and
  - `GIT_EXEC_PATH` points to that stand-in, so git cannot find its helper programs.
- **The parent is untouched.** Aria's own environment is never modified, so Aria can still commit and merge.
- **Accurate detection.** Only genuine git installation directories are removed, not unrelated folders whose names happen to contain "git".

## Limits

This is one layer of defense, not complete isolation. A worker that calls git by name, which is what AI coding assistants do, is refused. Commands that depend on git's helper programs, such as `git fetch` and `git submodule`, fail even when git is called by its full path. However, commands built directly into the git executable, such as `checkout`, can still run if a worker calls git by its full path. For that reason, Aria does not rely on the lockdown alone: Aria itself makes every commit and merge, and no change reaches the project until you accept it.

## Run the test

```
python test_git_lockdown.py
```

The test needs git installed. It builds a temporary repository and worktree, applies the lockdown, and checks that git is refused by name, that `fetch` and `submodule` fail even by full path, that the built-in `checkout` still runs by full path (the documented limit), and that the parent environment is unchanged.

Requires Python 3.11 or later. No third-party packages.
