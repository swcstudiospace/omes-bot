# Summary 21-01: Tweepy transport adapter and dependency

## What shipped

`omes/tools/x_tweepy.py`: `TweepyTransport` speaks the fake/stdlib transport
shape (`get(url, headers, params)` / `post(url, headers, body)`), routing v2
reads and writes to `tweepy.Client` (`get_me`, `get_users_mentions`,
`get_tweet`, `create_tweet`, all `user_auth=False`) and media upload plus
unknown paths to an optional raw fallback. The bearer token is taken per call
from the headers `XClient` resolved, so brokered and static credentials both
flow through unchanged. `tweepy.TweepyException` becomes `XError` naming the
endpoint, matching the other transports' failure shape.

`pyproject.toml` gains `dependencies = ["tweepy>=4.14"]` (verified against
4.17.0); `.github/workflows/ci.yml` installs the project before the suite.
No new tools, no roster change, no `x.py` change.

## Verification

- `.venv/bin/python -m pytest omes/tests/test_x_tweepy.py -q` → exit 0, 9 passed
  (mapping for all five operations, fallback routing, error/refusal paths,
  real-client construction without network).
- `.venv/bin/python -m pytest omes/tests -q` → exit 0, 135 passed (126 prior + 9).
- `.venv/bin/python -m omes.evals.runner omes/evals/cases` → exit 0, 6 passed.
- `bash omes/scripts/assemble-prompts.sh --check` → exit 0.

## Follow-ups

- OAuth1 user-context credentials for live posting (bearer-only like v3;
  the injectable client factory is the seam).
- Chunked media upload for bytes over 5 MiB (still refused, as in v3).
