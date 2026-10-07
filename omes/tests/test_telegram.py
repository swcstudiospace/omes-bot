"""Phase 25: the Telegram connector family behind a fake bot."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import aiogram
import pytest

from omes.credentials.broker import CredentialBroker
from omes.policy.policy import SeatPolicy
from omes.providers.base import ProviderError
from omes.tools.approvals import ApprovalLog
from omes.tools.registry import ToolRegistry
from omes.tools.telegram import TelegramClient, TelegramError, register_telegram_tools


class FakeChat:
    def __init__(self, chat_id: int):
        self.id = chat_id


class FakeMessage:
    def __init__(self, message_id: int, chat_id: int, text: str | None):
        self.message_id = message_id
        self.chat = FakeChat(chat_id)
        self.text = text
        self.date = datetime(2026, 10, 3, tzinfo=UTC)


class FakeUpdate:
    def __init__(self, update_id: int, message: FakeMessage | None):
        self.update_id = update_id
        self.message = message


class FakeSession:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class FakeBot:
    def __init__(self, token: str, updates: list | None = None):
        self.token = token
        self.calls: list[tuple] = []
        self.session = FakeSession()
        self._updates = updates if updates is not None else []
        self._next_id = 100

    async def get_updates(self, **kwargs):
        self.calls.append(("get_updates", kwargs))
        return self._updates

    async def send_message(self, **kwargs):
        self.calls.append(("send_message", kwargs))
        self._next_id += 1
        chat = kwargs["chat_id"]
        return FakeMessage(
            self._next_id, chat if isinstance(chat, int) else 7, kwargs["text"]
        )


def _bot_factory(updates: list | None = None):
    made: list[FakeBot] = []

    def make(token: str) -> FakeBot:
        bot = FakeBot(token, updates)
        made.append(bot)
        return bot

    return make, made


def _policy(hosts: list[str]) -> SeatPolicy:
    return SeatPolicy(
        {"version": 1, "tools": {}, "paths": {}, "network": {"hosts": hosts}}
    )


def _client(make, token: str = "tg-secret") -> TelegramClient:
    return TelegramClient(make, token=token)


def test_updates_map_to_serialized_shape():
    updates = [
        FakeUpdate(11, FakeMessage(1, 5, "hi")),
        FakeUpdate(12, None),
    ]
    make, made = _bot_factory(updates)
    result = _client(make).updates(offset=10, limit=25)
    assert result == {
        "updates": [
            {
                "update_id": 11,
                "kind": "message",
                "message": {
                    "message_id": 1,
                    "chat_id": 5,
                    "text": "hi",
                    "date": "2026-10-03T00:00:00+00:00",
                },
            },
            {"update_id": 12, "kind": "other", "message": None},
        ]
    }
    assert made[0].token == "tg-secret"
    assert made[0].calls == [("get_updates", {"limit": 25, "offset": 10})]
    assert made[0].session.closed is True


def test_send_maps_chat_text_and_reply():
    make, made = _bot_factory()
    result = _client(make).send(5, "hello", reply_to=3)
    assert result == {"message_id": 101, "chat_id": 5, "text": "hello"}
    assert made[0].calls == [
        ("send_message", {"chat_id": 5, "text": "hello", "reply_to_message_id": 3})
    ]
    assert made[0].session.closed is True


def test_bad_arguments_are_value_errors():
    make, _ = _bot_factory()
    client = _client(make)
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        client.updates(limit=0)
    with pytest.raises(ValueError, match="offset must be an integer"):
        # Intentional misuse: offset must be an integer.
        client.updates(offset="10")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="text must be a non-empty string"):
        client.send(5, "  ")
    with pytest.raises(ValueError, match="chat_id must be a chat id"):
        client.send("", "hi")
    with pytest.raises(ValueError, match="reply_to must be a message id integer"):
        # Intentional misuse: reply_to must be an integer.
        client.send(5, "hi", reply_to="3")  # type: ignore[arg-type]


def test_registry_reports_argument_errors_and_gates_sends():
    make, _ = _bot_factory([FakeUpdate(11, FakeMessage(1, 5, "hi"))])
    log = ApprovalLog()
    registry = ToolRegistry(approval_log=log)
    register_telegram_tools(registry, _client(make))

    assert (
        json.loads(registry.dispatch("telegram_updates", {}))["updates"][0]["update_id"]
        == 11
    )
    assert "error" in json.loads(
        registry.dispatch("telegram_send", {"chat_id": 5, "text": "  "})
    )
    assert json.loads(
        registry.dispatch("telegram_send", {"chat_id": 5, "text": "hi"})
    ) == {
        "error": "approval required",
        "tool": "telegram_send",
    }
    assert log.approve("telegram_send", "ada").get("approved") is True
    assert (
        json.loads(registry.dispatch("telegram_send", {"chat_id": 5, "text": "hi"}))[
            "text"
        ]
        == "hi"
    )


def test_brokered_token_flows_and_refused_host_runs_nothing():
    make, made = _bot_factory([FakeUpdate(11, FakeMessage(1, 5, "hi"))])
    broker = CredentialBroker(
        _policy(["api.telegram.org"]), {"TELEGRAM_BOT_TOKEN": "tg-live"}
    )
    client = TelegramClient(make).with_broker(broker)
    assert client.updates()["updates"][0]["update_id"] == 11
    assert made[0].token == "tg-live"

    denied = CredentialBroker(_policy([]), {"TELEGRAM_BOT_TOKEN": "tg-live"})
    blocked = TelegramClient(make).with_broker(denied)
    calls_before = len(made)
    with pytest.raises(ProviderError, match="no credential for host"):
        blocked.updates()
    assert len(made) == calls_before


def test_blank_token_is_refused_before_any_peer_call():
    make, made = _bot_factory()
    with pytest.raises(TelegramError, match="no Telegram credential"):
        TelegramClient(make, token="").updates()
    assert made == []


def test_library_failures_name_the_operation():
    class ExplodingBot(FakeBot):
        async def get_updates(self, **kwargs):
            raise aiogram.exceptions.TelegramAPIError(
                method=None,  # type: ignore[arg-type]
                message="boom",
            )

    def make(token: str) -> FakeBot:
        return ExplodingBot(token)

    with pytest.raises(TelegramError, match="telegram get updates"):
        TelegramClient(make, token="tg-secret").updates()


def test_default_factory_builds_a_real_bot():
    bot = TelegramClient().make_bot("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    assert isinstance(bot, aiogram.Bot)
    asyncio.run(bot.session.close())
