# Atomic task scheduler

Aria queues coding tasks and starts them as workers become available. This sample shows how a claim is atomic, so two claimers cannot take the same waiting task at the same time, even when several compete for the same queue. A task whose worker is lost goes back on the queue. A finished task is not claimed again.

## What it demonstrates

- **Atomic claims.** Claiming a task is a single SQLite `UPDATE ... RETURNING` statement inside an immediate transaction. The statement selects the oldest eligible task and marks it as running in one step, so two claimers can never take the same task.
- **A concurrency cap.** The limit on running tasks is checked inside the same statement, so it cannot be exceeded by a race.
- **A folder safety rule.** Tasks that work in their own copy of a project can run side by side on the same folder. Only one task at a time may edit a folder's live files directly.
- **Recovery from lost workers.** If a worker disappears, any task it was running returns to the queue instead of holding its slot forever. That task then runs again, so the guarantee is one worker per task at a time, not exactly one run per task.
- **Prompt wake-up.** The scheduler wakes as soon as work is added or finished, rather than waiting for its next timer tick.

The database runs in WAL mode, so readers are never blocked by a claim in progress.

## Run the test

```
python test_task_scheduler.py
```

The test starts eight threads that race to claim twenty tasks and verifies that every task is claimed exactly once. It also checks the cap, the folder rule, that finished tasks are never claimed again, recovery of a task whose worker is gone, and the wake-up signal.

Requires Python 3.11 or later and SQLite 3.35 or later (for `RETURNING`). No third-party packages.
