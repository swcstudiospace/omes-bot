# v3 research: X API v2 surface for the Grok Bot connector

Sources (fetched 2026-10-03):

- X API v2 endpoint references via skill registries (clawbird, x-api):
  POST /2/tweets, GET /2/tweets/:id, GET /2/users/me,
  GET /2/users/:id/mentions, GET /2/tweets/search/recent,
  all under https://api.x.com.

## Endpoints the connector uses

All JSON under `https://api.x.com` unless noted. Auth is a Bearer user
token (OAuth 2.0 user context) in tests via the broker's env mapping; no
live calls in this milestone.

- `GET /2/users/me` → `{"data": {"id", "name", "username"}}`. Resolves the
  bot's own user id once; mentions and posting need it.
- `GET /2/users/:id/mentions?max_results=&pagination_token=` →
  `{"data": [{tweet}], "meta": {"result_count", "next_token"}}`.
- `GET /2/tweets/:id?tweet.fields=...` → `{"data": {tweet}}`.
- `POST /2/tweets` with `{"text", "reply": {"in_reply_to_tweet_id"}}` →
  `{"data": {"id", "text"}}`. Threads chain `in_reply_to_tweet_id`.
- Media: `POST https://upload.twitter.com/1.1/media/upload.json` (simple
  upload for small bytes; `media_category=tweet_image`) →
  `{"media_id_string"}`. Attach via `POST /2/tweets`
  `{"text", "media": {"media_ids": [...]}}`.

## Error shape

Non-2xx responses carry `{"errors": [{"message", ...}]}` and/or
`{"title", "detail"}`. The connector surfaces `title`/`detail`/first error
message in failures; 429 and 5xx are retryable at the transport layer.

## What v3 borrows, and what stays out

- Read/write tweets, mentions, threads, simple media upload.
- Out: search, streaming, likes/follows/blocks, chunked media upload,
  OAuth flows (token arrives via the environment), quote posts, polls.
