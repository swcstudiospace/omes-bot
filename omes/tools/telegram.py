"""Telegram connector: updates and approval-gated sends behind brokered auth.

Speaks the Bot API through aiogram. Reads are plain registry tools;
sending (`telegram_send`) requires approval. Credentials resolve through
the broker per API host — the agent never handles the token. Tests run
behind a fake bot; no live Telegram calls.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import aiogram

from omes.tools.registry import ToolRegistry

# Offered after the X names. omes/contracts/tool-rosters/omes.yaml lists these.
TELEGRAM_TOOL_NAMES = (
    "telegram_updates",
    "telegram_send",
)

TELEGRAM_API_URL = "https://api.telegram.org"


class TelegramError(RuntimeError):
    """A Telegram failure, naming the operation and the API message."""


class _TelegramProvider:
    """Broker record: the token env var behind the `telegram` name."""

    name = "telegram"
    env_vars = ("TELEGRAM_BOT_TOKEN",)
    requires_key = True


def _default_bot(token: str) -> aiogram.Bot:
    return aiogram.Bot(token=token)


class TelegramClient:
    """One Telegram bot identity. `credentials(url)` wins over `token`."""

    def __init__(
        self,
        make_bot: Callable[[str], Any] | None = None,
        *,
        credentials: Any = None,
        token: str = "",
    ) -> None:
        self.make_bot = make_bot or _default_bot
        self._credentials = credentials
        self._token = token

    def with_broker(self, broker: Any) -> TelegramClient:
        """Return a copy resolving tokens through the broker per URL."""
        return TelegramClient(
            self.make_bot,
            credentials=lambda url: broker.key_for(_TelegramProvider(), url),
        )

    def updates(self, offset: int | None = None, limit: int = 10) -> dict[str, Any]:
        """Recent updates. Returns `{"updates": [...]}`."""
        _check_limit(limit)
        if offset is not None and (
            isinstance(offset, bool) or not isinstance(offset, int)
        ):
            raise ValueError("offset must be an integer")

        async def _fetch(bot: Any) -> Any:
            kwargs: dict[str, Any] = {"limit": limit}
            if offset is not None:
                kwargs["offset"] = offset
            return await bot.get_updates(**kwargs)

        raw = self._run("get updates", _fetch)
        return {"updates": [_serialize_update(update) for update in raw]}

    def send(
        self, chat_id: int | str, text: str, reply_to: int | None = None
    ) -> dict[str, Any]:
        """Send one message. Returns `{"message_id", "chat_id", "text"}`."""
        target = _check_chat(chat_id)
        _check_text(text)
        if reply_to is not None and (
            isinstance(reply_to, bool) or not isinstance(reply_to, int)
        ):
            raise ValueError("reply_to must be a message id integer")

        async def _post(bot: Any) -> Any:
            kwargs: dict[str, Any] = {"chat_id": target, "text": text}
            if reply_to is not None:
                kwargs["reply_to_message_id"] = reply_to
            return await bot.send_message(**kwargs)

        sent = self._run("send message", _post)
        return {
            "message_id": sent.message_id,
            "chat_id": sent.chat.id,
            "text": sent.text,
        }

    def _run(self, operation: str, action: Callable[[Any], Any]) -> Any:
        token = self._resolve_token()
        factory = self.make_bot

        async def _session() -> Any:
            bot = factory(token)
            try:
                return await action(bot)
            finally:
                close = getattr(getattr(bot, "session", None), "close", None)
                if callable(close):
                    await close()

        try:
            return asyncio.run(_session())
        except TelegramError:
            raise
        except Exception as exc:
            raise TelegramError(f"telegram {operation}: {exc}") from exc

    def _resolve_token(self) -> str:
        if self._credentials is not None:
            token = self._credentials(TELEGRAM_API_URL)
        else:
            token = self._token
        if not isinstance(token, str) or not token:
            raise TelegramError(
                "no Telegram credential: broker refused or token is blank"
            )
        return token


def _serialize_update(update: Any) -> dict[str, Any]:
    message = getattr(update, "message", None)
    if message is None:
        return {"update_id": update.update_id, "kind": "other", "message": None}
    date = getattr(message, "date", None)
    return {
        "update_id": update.update_id,
        "kind": "message",
        "message": {
            "message_id": message.message_id,
            "chat_id": message.chat.id,
            "text": message.text,
            "date": (
                date.isoformat()
                if date is not None and hasattr(date, "isoformat")
                else date
            ),
        },
    }


def _check_limit(limit: Any) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")


def _check_chat(chat_id: Any) -> int | str:
    if isinstance(chat_id, bool):
        raise ValueError("chat_id must be a chat id")
    if isinstance(chat_id, int):
        return chat_id
    if isinstance(chat_id, str) and chat_id != "":
        return chat_id
    raise ValueError("chat_id must be a chat id")


def _check_text(text: Any) -> None:
    if not isinstance(text, str) or text.strip() == "":
        raise ValueError("text must be a non-empty string")


def register_telegram_tools(
    registry: ToolRegistry, client: TelegramClient
) -> list[str]:
    """Register the two Telegram tools. Sending requires approval."""

    def telegram_updates(offset: int | None = None, limit: int = 10) -> dict[str, Any]:
        try:
            return client.updates(offset=offset, limit=limit)
        except (TelegramError, ValueError) as exc:
            return {"error": str(exc)}

    def telegram_send(
        chat_id: int | str, text: str, reply_to: int | None = None
    ) -> dict[str, Any]:
        try:
            return client.send(chat_id, text, reply_to=reply_to)
        except (TelegramError, ValueError) as exc:
            return {"error": str(exc)}

    handlers: dict[str, Callable[..., Any]] = {
        "telegram_updates": telegram_updates,
        "telegram_send": telegram_send,
    }
    if set(handlers) != set(TELEGRAM_TOOL_NAMES):
        raise RuntimeError("Telegram tool handlers drifted from TELEGRAM_TOOL_NAMES")
    for name in TELEGRAM_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=(name == "telegram_send"),
        )
    return list(TELEGRAM_TOOL_NAMES)


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "telegram_updates": (
        "Read recent Telegram updates for the bot. Read-only; no approval needed.",
        {
            "type": "object",
            "properties": {
                "offset": {
                    "type": "integer",
                    "description": "Update offset to resume from.",
                },
                "limit": {"type": "integer", "description": "1-100. Defaults to 10."},
            },
            "required": [],
        },
    ),
    "telegram_send": (
        "Send one Telegram message, optionally as a reply. Requires approval.",
        {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": ["integer", "string"],
                    "description": "Chat id or @channel.",
                },
                "text": {"type": "string", "description": "Message text."},
                "reply_to": {
                    "type": "integer",
                    "description": "Message id to reply to.",
                },
            },
            "required": ["chat_id", "text"],
        },
    ),
}


__all__ = [
    "TELEGRAM_API_URL",
    "TELEGRAM_TOOL_NAMES",
    "TelegramClient",
    "TelegramError",
    "register_telegram_tools",
]
