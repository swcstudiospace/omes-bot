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

Omega Prime is built to keep secrets out of reach:

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
  verifications (`omega_prime/tests/test_web.py` and `omega_prime/tests/test_browser_egress.py`).

## Dependency exceptions

`requirements-lock.txt` pins `oauthlib==3.3.1` because `tweepy==4.17.0`
requires `oauthlib>=3.2.0,<4`. [PYSEC-2026-4114](https://osv.dev/vulnerability/PYSEC-2026-4114)
is a PKCE timing oracle in oauthlib's authorization-server grant
(`code_challenge_method_plain` / `code_challenge_method_s256`). Omega Prime
does not host that grant. The supply-chain workflow ignores only that
advisory, against the lockfile, until a tweepy release accepts `oauthlib>=4`.
The runner's own `pip` is not part of the audit.
