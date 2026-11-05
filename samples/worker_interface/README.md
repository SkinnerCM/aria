# Worker interface

Aria can use several different AI coding assistants as workers: Grok Build, Claude Code, and Codex. Each one is connected through this common interface, so the rest of Aria never depends on the details of a single assistant.

## What it demonstrates

- **Two checks before any work starts.** The interface answers two questions: is the program installed, and is it already logged in? Only when both answers are yes is the worker started and given the one folder it is allowed to change.
- **Clear failures.** A missing program is reported as missing, with an install hint. A program that is installed but not logged in is reported as not ready. Neither case starts a worker that would hang while waiting for a login nobody can see.
- **No secrets in status reports.** Login status is described in words, and the credential itself never appears in the result.
- **Usage accounting.** Token counts and cost are read from each worker's result, and malformed values are ignored rather than trusted.
- **Workers edit files only.** The base `run` method deliberately does nothing; each real worker provides its own. Workers never commit, push, or merge. Aria makes the commits, and it merges only after you accept the work. The worker's restricted environment is shown in the [git lockdown sample](../git_lockdown).

This sample contains the interface only. It does not include any real coding assistant or the adapters that drive them.

## Run the test

```
python test_worker_interface.py
```

The test uses stand-in programs to confirm that a missing program, an installed program, and a program without a login are each reported correctly, that malformed usage values are dropped, and that the base worker does not edit files.

Requires Python 3.11 or later. No third-party packages.
