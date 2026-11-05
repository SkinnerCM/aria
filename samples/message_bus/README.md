# Message bus with authenticated senders

Aria's director, project managers, and coding workers communicate through a single message bus. This sample shows the core of that design: an append-only log with live delivery, history for late readers, and sender identities that cannot be forged.

## What it demonstrates

- **Live delivery.** Every listener receives each new message as soon as it is published.
- **History for late readers.** A worker that starts after the plan was written can read every message after a given ID, so it never has to guess what it missed.
- **Authenticated sender names.** Anyone can put any name on a message, so a name alone proves nothing. The bus accepts a privileged name, such as `director`, `manager:3`, or `worker:7`, only when the sender presents a token that the bus itself issued for that exact name. A missing, wrong, or borrowed token causes the message to be recorded as coming from an `outsider`.

Tokens are HMAC-SHA256 signatures over the sender name, keyed with a random secret that never leaves the bus. Only code running inside Aria can obtain a token. Token comparison is constant-time.

## Run the test

```
python test_message_bus.py
```

The test checks live delivery, history replay, a forged director message with no token, a valid token used for the wrong name, a token from a different bus instance, and that history returns copies that callers cannot use to alter the log.

Requires Python 3.11 or later. No third-party packages.
