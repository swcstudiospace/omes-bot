---
phase: 17-x-connector
plan: 01
subsystem: tools
tags: [x, connector, publishing, approvals]
provides:
  - X reads, approval-gated publishing, staged media
affects: [18-engagement-sweep]
---

# Phase 17 summary

`XClient` speaks X API v2 (`me`, mentions with pagination, single posts, post with reply/media, chained threads) plus simple media upload, with tokens from a direct string or resolved per URL through the broker (`X_API_TOKEN`). Transport failures surface as `XError` naming the endpoint; broker refusals stay `ProviderError`. Five registry tools expose the client; `x_post` and `x_post_thread` require approval, reads and staging do not. The `Transport` protocol plus both transports gained `get` (HTTP shares POST's retry/timeout/allowlist path), recorded calls are uniform 4-tuples, the roster lists the X family after IDE, the shipped policy allows all 28 names, and plan mode blocks the three publishing tools.

## Verification

Command: `python3 -m pytest omes/tests -q`

Exit code: 0

Output tail: `118 passed in 3.81s` (`test_x.py`: 5 passed)

Unverified: live X endpoints, search, streaming, likes/follows, chunked upload, OAuth flows.
