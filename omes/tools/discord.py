"""Discord connector: channel reads and approval-gated sends behind brokered auth.

Speaks the Discord API through discord.py over REST only: per call the
client logs in, fetches the channel, reads history or sends, and closes.
No gateway connection is opened. Reads are plain registry tools; sending
(`discord_send`) requires approval. Credentials resolve through the broker
per API host. Tests run behind fake peers; no live Discord calls.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

import discord

from omes.tools.registry import ToolRegistry

# Offered after the Telegram names. omes/contracts/tool-rosters/omes.yaml lists these.
DISCORD_TOOL_NAMES = (
    "discord_read",
    "discord_send",
)

DISCORD_API_URL = "https://discord.com"


class DiscordError(RuntimeError):
    """A Discord failure, naming the operation and the API message."""


class _DiscordProvider:
    """Broker record: the token env var behind the `discord` name."""

    name = "discord"
    env_vars = ("DISCORD_BOT_TOKEN",)
    requires_key = True


def _default_client() -> discord.Client:
    return discord.Client(intents=discord.Intents.default())


class DiscordClient:
    """One Discord bot identity. `credentials(url)` wins over `token`."""

    def __init__(
        self,
        make_client: Callable[[], Any] | None = None,
        *,
        credentials: Any = None,
        token: str = "",
    ) -> None:
        self.make_client = make_client or _default_client
        self._credentials = credentials
        self._token = token

    def with_broker(self, broker: Any) -> DiscordClient:
        """Return a copy resolving tokens through the broker per URL."""
        return DiscordClient(
            self.make_client,
            credentials=lambda url: broker.key_for(_DiscordProvider(), url),
        )

    def read(self, channel_id: int | str, limit: int = 10) -> dict[str, Any]:
        """Recent messages in a channel. Returns `{"messages": [...]}`."""
        target = _check_channel(channel_id)
        _check_limit(limit)

        async def _fetch(client: Any) -> Any:
            channel = await client.fetch_channel(target)
            return [message async for message in channel.history(limit=limit)]

        raw = self._run("read channel", _fetch)
        return {"messages": [_serialize_message(message) for message in raw]}

    def send(self, channel_id: int | str, text: str) -> dict[str, Any]:
        """Send one message. Returns `{"id", "channel_id", "content"}`."""
        target = _check_channel(channel_id)
        _check_text(text)

        async def _post(client: Any) -> Any:
            channel = await client.fetch_channel(target)
            return await channel.send(text)

        sent = self._run("send message", _post)
        return {
            "id": str(sent.id),
            "channel_id": str(getattr(getattr(sent, "channel", None), "id", target)),
            "content": sent.content,
        }

    def _run(self, operation: str, action: Callable[[Any], Any]) -> Any:
        token = self._resolve_token()
        factory = self.make_client

        async def _session() -> Any:
            client = factory()
            try:
                await client.login(token)
                return await action(client)
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    await close()

        try:
            return asyncio.run(_session())
        except DiscordError:
            raise
        except Exception as exc:
            raise DiscordError(f"discord {operation}: {exc}") from exc

    def _resolve_token(self) -> str:
        if self._credentials is not None:
            token = self._credentials(DISCORD_API_URL)
        else:
            token = self._token
        if not isinstance(token, str) or not token:
            raise DiscordError("no Discord credential: broker refused or token is blank")
        return token


def _serialize_message(message: Any) -> dict[str, Any]:
    created = getattr(message, "created_at", None)
    author = getattr(message, "author", None)
    return {
        "id": str(message.id),
        "content": message.content,
        "author": str(getattr(author, "name", author)),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
    }


def _check_channel(channel_id: Any) -> int:
    if isinstance(channel_id, bool):
        raise ValueError("channel_id must be a channel id")
    if isinstance(channel_id, int):
        return channel_id
    if isinstance(channel_id, str) and channel_id.isdigit():
        return int(channel_id)
    raise ValueError("channel_id must be a channel id")


def _check_limit(limit: Any) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")


def _check_text(text: Any) -> None:
    if not isinstance(text, str) or text.strip() == "":
        raise ValueError("text must be a non-empty string")


def register_discord_tools(registry: ToolRegistry, client: DiscordClient) -> list[str]:
    """Register the two Discord tools. Sending requires approval."""

    def discord_read(channel_id: int | str, limit: int = 10) -> dict[str, Any]:
        try:
            return client.read(channel_id, limit=limit)
        except (DiscordError, ValueError) as exc:
            return {"error": str(exc)}

    def discord_send(channel_id: int | str, text: str) -> dict[str, Any]:
        try:
            return client.send(channel_id, text)
        except (DiscordError, ValueError) as exc:
            return {"error": str(exc)}

    handlers = {
        "discord_read": discord_read,
        "discord_send": discord_send,
    }
    if set(handlers) != set(DISCORD_TOOL_NAMES):
        raise RuntimeError("Discord tool handlers drifted from DISCORD_TOOL_NAMES")
    for name in DISCORD_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=(name == "discord_send"),
        )
    return list(DISCORD_TOOL_NAMES)


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "discord_read": (
        "Read recent Discord messages in a channel. Read-only; no approval needed.",
        {
            "type": "object",
            "properties": {
                "channel_id": {"type": ["integer", "string"], "description": "Channel id."},
                "limit": {"type": "integer", "description": "1-100. Defaults to 10."},
            },
            "required": ["channel_id"],
        },
    ),
    "discord_send": (
        "Send one Discord message to a channel. Requires approval.",
        {
            "type": "object",
            "properties": {
                "channel_id": {"type": ["integer", "string"], "description": "Channel id."},
                "text": {"type": "string", "description": "Message text."},
            },
            "required": ["channel_id", "text"],
        },
    ),
}


__all__ = [
    "DISCORD_API_URL",
    "DISCORD_TOOL_NAMES",
    "DiscordClient",
    "DiscordError",
    "register_discord_tools",
]
