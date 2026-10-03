"""X connector: mentions, posts, threads, and media behind brokered auth.

Speaks X API v2 (`https://api.x.com`) plus simple media upload
(`https://upload.twitter.com/1.1/media/upload.json`). Reads are plain
registry tools; publishing (`x_post`, `x_post_thread`) requires approval.
Credentials resolve through the broker per endpoint — the agent never
handles the token. Tests run behind a fake transport; no live X calls.
"""

from __future__ import annotations

import base64
import binascii
from typing import Any
from urllib.parse import quote

from omes.providers.base import ProviderError
from omes.tools.registry import ToolRegistry

# Offered after the IDE names. omes/contracts/tool-rosters/omes.yaml lists these.
X_TOOL_NAMES = (
    "x_mentions",
    "x_read_post",
    "x_post",
    "x_post_thread",
    "x_upload_media",
)

DEFAULT_BASE_URL = "https://api.x.com"
DEFAULT_UPLOAD_URL = "https://upload.twitter.com"
MAX_MEDIA_BYTES = 5 * 1024 * 1024


class XError(RuntimeError):
    """An X API failure, naming the endpoint and the API message."""


class _XProvider:
    """Broker record: the token env var behind the `x` name."""

    name = "x"
    env_vars = ("X_API_TOKEN",)
    requires_key = True


class XClient:
    """One X API identity. `credentials(url)` wins over `token`."""

    def __init__(
        self,
        transport: Any,
        *,
        base_url: str = DEFAULT_BASE_URL,
        upload_url: str = DEFAULT_UPLOAD_URL,
        credentials: Any = None,
        token: str = "",
    ) -> None:
        self.transport = transport
        self.base_url = base_url.rstrip("/")
        self.upload_url = upload_url.rstrip("/")
        self._credentials = credentials
        self._token = token

    def with_broker(self, broker: Any) -> XClient:
        """Return a copy resolving tokens through the broker per URL."""
        return XClient(
            self.transport,
            base_url=self.base_url,
            upload_url=self.upload_url,
            credentials=lambda url: broker.key_for(_XProvider(), url),
        )

    def me(self) -> dict:
        """The bot's own user record."""
        data = self._get(f"{self.base_url}/2/users/me", {})
        user = data.get("data")
        if not isinstance(user, dict) or not user.get("id"):
            raise XError("GET /2/users/me returned no user")
        return user

    def mentions(
        self,
        user_id: str | None = None,
        max_results: int = 10,
        pagination_token: str | None = None,
    ) -> dict:
        """Recent mentions, newest first per the API."""
        if isinstance(max_results, bool) or not isinstance(max_results, int):
            raise ValueError("max_results must be an integer")
        if not 1 <= max_results <= 100:
            raise ValueError("max_results must be between 1 and 100")
        resolved = user_id or self.me()["id"]
        params: dict[str, Any] = {"max_results": max_results}
        if pagination_token:
            params["pagination_token"] = pagination_token
        data = self._get(
            f"{self.base_url}/2/users/{quote(str(resolved), safe='')}/mentions", params
        )
        posts = data.get("data", [])
        if posts is None:
            posts = []
        if not isinstance(posts, list):
            raise XError("mentions returned no post list")
        result: dict[str, Any] = {"posts": posts}
        meta = data.get("meta")
        if isinstance(meta, dict) and meta.get("next_token"):
            result["next_token"] = meta["next_token"]
        return result

    def read_post(self, post_id: str) -> dict:
        """One post by id."""
        if not isinstance(post_id, str) or post_id == "":
            raise ValueError("post_id must be a non-empty string")
        data = self._get(f"{self.base_url}/2/tweets/{quote(post_id, safe='')}", {})
        post = data.get("data")
        if not isinstance(post, dict):
            raise XError(f"GET /2/tweets/{post_id} returned no post")
        return post

    def post(
        self,
        text: str,
        reply_to: str | None = None,
        media_ids: list[str] | None = None,
    ) -> dict:
        """Publish one post. Returns `{"id", "text"}`."""
        _check_text(text)
        body: dict[str, Any] = {"text": text}
        if reply_to:
            body["reply"] = {"in_reply_to_tweet_id": str(reply_to)}
        if media_ids:
            body["media"] = {"media_ids": [str(media_id) for media_id in media_ids]}
        data = self._post(f"{self.base_url}/2/tweets", body)
        created = data.get("data")
        if not isinstance(created, dict) or not created.get("id"):
            raise XError("POST /2/tweets returned no post")
        return created

    def thread(self, texts: list[str], reply_to: str | None = None) -> list[dict]:
        """Publish each text as a reply to the previous. Returns each post."""
        if not isinstance(texts, list) or not texts:
            raise ValueError("texts must be a non-empty list")
        for text in texts:
            _check_text(text)
        published: list[dict] = []
        parent = reply_to
        for text in texts:
            created = self.post(text, reply_to=parent)
            published.append(created)
            parent = created["id"]
        return published

    def upload_media(self, data: bytes, mime: str = "image/png") -> dict:
        """Stage media bytes. Returns `{"media_id"}`."""
        if not isinstance(data, bytes) or not data:
            raise ValueError("data must be non-empty bytes")
        if len(data) > MAX_MEDIA_BYTES:
            raise ValueError("media exceeds the 5 MiB simple-upload limit")
        if not isinstance(mime, str) or "/" not in mime:
            raise ValueError("mime must look like type/subtype")
        payload = self._post(
            f"{self.upload_url}/1.1/media/upload.json",
            {"media_data": base64.b64encode(data).decode("ascii"), "media_category": "tweet_image"},
        )
        media_id = payload.get("media_id_string")
        if not media_id:
            raise XError("media upload returned no media id")
        return {"media_id": str(media_id)}

    def _headers(self, url: str) -> dict:
        if self._credentials is not None:
            token = self._credentials(url)
        else:
            token = self._token
        if not isinstance(token, str) or not token:
            raise XError("no X credential: broker refused or token is blank")
        return {"Authorization": f"Bearer {token}"}

    def _get(self, url: str, params: dict) -> dict:
        try:
            return self.transport.get(url, self._headers(url), params)
        except Exception as exc:
            raise _wrap(exc, url) from exc

    def _post(self, url: str, body: dict) -> dict:
        try:
            return self.transport.post(url, self._headers(url), body)
        except Exception as exc:
            raise _wrap(exc, url) from exc


def _wrap(exc: Exception, url: str) -> Exception:
    if isinstance(exc, (XError, ProviderError)):
        return exc
    message = str(exc) or type(exc).__name__
    endpoint = url.split("://", 1)[-1].split("/", 1)[-1]
    return XError(f"{endpoint or url}: {message}")


def _check_text(text: Any) -> None:
    if not isinstance(text, str) or text.strip() == "":
        raise ValueError("text must be a non-empty string")


def register_x_tools(registry: ToolRegistry, client: XClient) -> list[str]:
    """Register the five X tools. Publishing requires approval."""

    def x_mentions(
        user_id: str | None = None, max_results: int = 10
    ) -> dict[str, Any]:
        try:
            return client.mentions(user_id=user_id, max_results=max_results)
        except (XError, ValueError) as exc:
            return {"error": str(exc)}

    def x_read_post(post_id: str) -> dict[str, Any]:
        try:
            return client.read_post(post_id)
        except (XError, ValueError) as exc:
            return {"error": str(exc)}

    def x_post(
        text: str,
        reply_to: str | None = None,
        media_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            return client.post(text, reply_to=reply_to, media_ids=media_ids)
        except (XError, ValueError) as exc:
            return {"error": str(exc)}

    def x_post_thread(texts: list[str], reply_to: str | None = None) -> dict[str, Any]:
        try:
            return {"posts": client.thread(texts, reply_to=reply_to)}
        except (XError, ValueError) as exc:
            return {"error": str(exc)}

    def x_upload_media(data_b64: str, mime: str = "image/png") -> dict[str, Any]:
        if not isinstance(data_b64, str) or data_b64 == "":
            return {"error": "data_b64 must be a non-empty base64 string"}
        try:
            data = base64.b64decode(data_b64, validate=True)
        except (binascii.Error, ValueError):
            return {"error": "data_b64 is not valid base64"}
        try:
            return client.upload_media(data, mime=mime)
        except (XError, ValueError) as exc:
            return {"error": str(exc)}

    handlers = {
        "x_mentions": x_mentions,
        "x_read_post": x_read_post,
        "x_post": x_post,
        "x_post_thread": x_post_thread,
        "x_upload_media": x_upload_media,
    }
    if set(handlers) != set(X_TOOL_NAMES):
        raise RuntimeError("X tool handlers drifted from X_TOOL_NAMES")
    approvals = {"x_post", "x_post_thread"}
    for name in X_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name, description, parameters, handlers[name], requires_approval=name in approvals
        )
    return list(X_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "x_mentions": (
        "Read recent mentions of an X user (defaults to the bot itself). "
        "Read-only; no approval needed.",
        _object(
            {
                "user_id": _string("X user id. Defaults to the bot's own id."),
                "max_results": {"type": "integer", "description": "1-100. Defaults to 10."},
            },
            [],
        ),
    ),
    "x_read_post": (
        "Read one X post by id. Read-only; no approval needed.",
        _object({"post_id": _string("Post id.")}, ["post_id"]),
    ),
    "x_post": (
        "Publish one X post, optionally as a reply or with staged media. "
        "Requires approval.",
        _object(
            {
                "text": _string("Post text."),
                "reply_to": _string("Post id to reply to."),
                "media_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Staged media ids from x_upload_media.",
                },
            },
            ["text"],
        ),
    ),
    "x_post_thread": (
        "Publish a thread: each text replies to the previous. Requires approval.",
        _object(
            {
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Post texts in order.",
                },
                "reply_to": _string("Post id the first text replies to."),
            },
            ["texts"],
        ),
    ),
    "x_upload_media": (
        "Stage media bytes for a later post. Returns a media id.",
        _object(
            {
                "data_b64": _string("Base64 media bytes, at most 5 MiB decoded."),
                "mime": _string("MIME type. Defaults to image/png."),
            },
            ["data_b64"],
        ),
    ),
}


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_UPLOAD_URL",
    "MAX_MEDIA_BYTES",
    "XClient",
    "XError",
    "X_TOOL_NAMES",
    "register_x_tools",
]
