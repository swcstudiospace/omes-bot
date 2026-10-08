# Security Policy

## Reporting a vulnerability

**Do not open a public issue.** Report through a private GitHub Security
Advisory on this repository
(`Security` tab → `Report a vulnerability`). Include:

- What is affected (tool, transport, prompt, workflow)
- Steps to reproduce, with the smallest possible example
- What you expected to happen vs. what happened

We aim to acknowledge reports promptly, keep the fix quiet until a release
is cut, and credit reporters who want credit.

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes |
| < 0.1 | No (pre-release history) |

## Secrets posture

Omes is built to keep secrets out of reach:

- Keys resolve from the environment through the credential broker and are
  redacted from transcripts, events, errors, and eval output.
- Tool arguments are never logged and never leave the process in event
  summaries.
- Tests are hermetic — no live credentials exist in CI.
- If you find a secret committed anywhere in history, report it as above
  so it can be rotated and purged; do not quote it in an issue or PR.

## Network & Browser Hardening

Network operations and browser sessions enforce fail-closed egress boundaries:

- Destination policy: `DestinationTransport` strictly validates hostnames, port ranges
  (1–65535), IP classification, and authority framing. Private, loopback, and reserved
  ranges refuse before dial.
- Browser sandbox confinement: `GuardedBrowserFactory` validates accounting receipts,
  cgroup lifecycle, and socket tracking. Unverified sandbox environments fail closed.
- Test coverage and evidence are validated through hermetic test suites and runtime
  verifications (`omes/tests/test_web.py` and `omes/tests/test_browser_egress.py`).
