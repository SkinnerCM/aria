# Cross-platform live terminals

Each coding worker in Aria runs in a real terminal session, and you can watch every session live in the browser. This sample shows the core of that: one pseudo-terminal session that works the same way on Windows and macOS.

## What it demonstrates

- **Native pseudo-terminals on both platforms.** On Windows, the session uses ConPTY through `pywinpty`. On macOS and Linux, it uses `ptyprocess`. Both sit behind the same small interface.
- **Continuous capture.** A background thread reads output as the program produces it, so a slow reader never stalls the program.
- **Late attach.** Recent output is kept in a bounded buffer, so a screen that connects after a session has started can still show what already happened.
- **Clean shutdown.** Closing a session terminates the program and stops the reader thread.

## Run the test

```
pip install -r requirements.txt
python test_terminals.py
```

The test starts a short Python program inside a terminal session and confirms that its output is read back through the session.

Requires Python 3.11 or later. `pywinpty` is needed on Windows and `ptyprocess` elsewhere, both pinned in `requirements.txt`.
