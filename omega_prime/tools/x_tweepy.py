"""Live X transport on `tweepy.Client`.

Speaks the same `get(url, headers, params)` / `post(url, headers, body)`
shape as the fake and stdlib transports, so `XClient` needs no changes:
construct it with this transport and the bearer `XClient` already resolved
(per call, broker or static token) builds the v2 client. `tweepy.Client` is
v2-only, so media upload routes to a fallback raw transport.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import unquote, urlparse

import tweepy

from omega_prime.tools.x import DEFAULT_BASE_URL, DEFAULT_UPLOAD_URL, XError


def _default_client(token: str) -> tweepy.Client:
    return tweepy.Client(bearer_token=token)


class TweepyTransport:
    """Route X API URLs to `tweepy.Client` methods.

    `make_client(token)` builds the v2 client; tests inject a stub. Upload
    posts (and any unknown path) go to `fallback` when one is set.
    """

    def __init__(
        self,
        *,
        make_client: Callable[[str], Any] | None = None,
        fallback: Any = None,
        base_url: str = DEFAULT_BASE_URL,
        upload_url: str = DEFAULT_UPLOAD_URL,
    ) -> None:
        self.make_client = make_client or _default_client
        self.fallback = fallback
        self.base_url = base_url.rstrip("/")
        self.upload_url = upload_url.rstrip("/")

    def get(self, url: str, headers: dict, params: dict) -> dict:
        """GET one v2 read through the client built from the bearer token."""
        token = _bearer(headers)
        path = _path(url)
        try:
            client = self.make_client(token)
            if path == "/2/users/me":
                return {"data": client.get_me(user_auth=False).data}
            if path.startswith("/2/users/") and path.endswith("/mentions"):
                user_id = unquote(path[len("/2/users/") : -len("/mentions")])
                response = client.get_users_mentions(
                    user_id,
                    **_pick(params, ("max_results", "pagination_token")),
                    user_auth=False,
                )
                return {"data": response.data, "meta": response.meta or {}}
            if path.startswith("/2/tweets/"):
                post_id = unquote(path[len("/2/tweets/") :])
                return {"data": client.get_tweet(post_id, user_auth=False).data}
        except tweepy.TweepyException as exc:
            raise XError(f"{_endpoint(url)}: {exc}") from exc
        if self.fallback is not None:
            return self.fallback.get(url, headers, params)
        raise XError(f"{_endpoint(url)}: unsupported tweepy transport path")

    def post(self, url: str, headers: dict, body: dict) -> dict:
        """POST one v2 write; upload posts go to the raw fallback."""
        token = _bearer(headers)
        path = _path(url)
        if path == "/2/tweets" and url.startswith(self.base_url):
            try:
                client = self.make_client(token)
                reply = body.get("reply") or {}
                media = body.get("media") or {}
                kwargs: dict[str, Any] = {"text": body.get("text"), "user_auth": False}
                if reply.get("in_reply_to_tweet_id") is not None:
                    kwargs["in_reply_to_tweet_id"] = str(reply["in_reply_to_tweet_id"])
                if media.get("media_ids") is not None:
                    kwargs["media_ids"] = [str(mid) for mid in media["media_ids"]]
                return {"data": client.create_tweet(**kwargs).data}
            except tweepy.TweepyException as exc:
                raise XError(f"{_endpoint(url)}: {exc}") from exc
        if self.fallback is not None:
            return self.fallback.post(url, headers, body)
        if url.startswith(self.upload_url):
            raise XError(
                f"{_endpoint(url)}: media upload needs a raw HTTP fallback "
                "(tweepy.Client is v2-only)"
            )
        raise XError(f"{_endpoint(url)}: unsupported tweepy transport path")


def _bearer(headers: Any) -> str:
    value = headers.get("Authorization") if isinstance(headers, dict) else None
    if not isinstance(value, str) or not value.startswith("Bearer "):
        raise XError("no X credential: transport saw no bearer token")
    token = value[len("Bearer ") :]
    if token.strip() == "":
        raise XError("no X credential: transport saw a blank bearer token")
    return token


def _path(url: str) -> str:
    return urlparse(url).path or ""


def _endpoint(url: str) -> str:
    return url.split("://", 1)[-1].split("/", 1)[-1]


def _pick(params: Any, names: tuple[str, ...]) -> dict:
    if not isinstance(params, dict):
        return {}
    return {name: params[name] for name in names if params.get(name) is not None}


__all__ = ["TweepyTransport"]
