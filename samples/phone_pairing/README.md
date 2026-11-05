# One-time phone pairing

Aria lets you pair a phone so you can check on work and send instructions away from your desk. This sample shows the pairing handshake, designed so that a photographed or forwarded QR code is useless on its own.

## How pairing works

1. Aria creates an invitation and shows a QR code on your computer's screen, along with a short approval code.
2. The QR code contains only the invitation ID. The approval code is never in the picture.
3. You scan the QR code with your phone and type in the approval code from your computer's screen.
4. If both match, the phone receives its own session credential, and the invitation can never be used again.

## What it demonstrates

- **Single use.** An invitation is consumed the moment it is accepted.
- **Expiry.** An invitation stops working after a short time limit.
- **Limited attempts.** After a small number of wrong approval codes, the invitation is locked.
- **No stored secrets.** Aria keeps only SHA-256 hashes of approval codes and session credentials, never the values themselves.
- **Consistent failures.** Every rejected pairing attempt returns the same error message, and credential comparisons use constant-time digest comparisons.
- **Housekeeping.** Used and expired invitations are removed when new invitations are created.

## Run the test

```
python test_phone_pairing.py
```

The test covers a successful pairing, reuse of an accepted invitation, expiry, the attempt limit, an unknown invitation, and that the approval code never appears in the QR payload.

Requires Python 3.11 or later. No third-party packages.
