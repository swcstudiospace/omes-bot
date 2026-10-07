"""Phase 25: the Discord connector family behind fake peers."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

try:
    import discord
except ImportError:  # Python 3.13+: audioop removal breaks discord.py's import
    discord = None  # type: ignore[assignment]

from omes.credentials.broker import CredentialBroker
from omes.policy.policy import SeatPolicy
from omes.providers.base import ProviderError
from omes.tools.approvals import ApprovalLog
from omes.tools.discord import DiscordClient, DiscordError, register_discord_tools
from omes.tools.registry import ToolRegistry


class FakeAuthor:
    def __init__(self, name: str):
        self.name = name


class FakeMessage:
    def __init__(self, message_id: int, channel_id: int, content: str):
        self.id = message_id
        self.channel = FakeChannel(channel_id, [])
        self.content = content
        self.author = FakeAuthor("ada")
        self.created_at = datetime(2026, 10, 3, tzinfo=UTC)


class FakeChannel:
    def __init__(self, channel_id: int, messages: list):
        self.id = channel_id
        self.messages = messages
        self.calls: list[tuple] = []
        self._next_id = 500

    def history(self, *, limit: int = 100):
        self.calls.append(("history", limit))

        async def _generate():
            for message in self.messages[:limit]:
                yield message

        return _generate()

    async def send(self, content: str):
        self.calls.append(("send", content))
        self._next_id += 1
        return FakeMessage(self._next_id, self.id, content)


class FakeDiscordClient:
    def __init__(self, channels: dict | None = None):
        self.calls: list[tuple] = []
        self.channels = channels or {}
        self.closed = False

    async def login(self, token: str):
        self.calls.append(("login", token))

    async def fetch_channel(self, channel_id: int):
        self.calls.append(("fetch_channel", channel_id))
        return self.channels[channel_id]

    async def close(self):
        self.closed = True


def _client_factory(channels: dict | None = None):
    made: list[FakeDiscordClient] = []

    def make() -> FakeDiscordClient:
        peer = FakeDiscordClient(channels)
        made.append(peer)
        return peer

    return make, made


def _policy(hosts: list[str]) -> SeatPolicy:
    return SeatPolicy(
        {"version": 1, "tools": {}, "paths": {}, "network": {"hosts": hosts}}
    )


def _client(make, token: str = "dc-secret") -> DiscordClient:
    return DiscordClient(make, token=token)


def _channels() -> dict:
    return {
        9: FakeChannel(
            9,
            [
                FakeMessage(21, 9, "first"),
                FakeMessage(22, 9, "second"),
            ],
        )
    }


def test_read_maps_to_serialized_shape():
    make, made = _client_factory(_channels())
    result = _client(make).read(9, limit=2)
    assert result == {
        "messages": [
            {
                "id": "21",
                "content": "first",
                "author": "ada",
                "created_at": "2026-10-03T00:00:00+00:00",
            },
            {
                "id": "22",
                "content": "second",
                "author": "ada",
                "created_at": "2026-10-03T00:00:00+00:00",
            },
        ]
    }
    assert made[0].calls == [("login", "dc-secret"), ("fetch_channel", 9)]
    assert made[0].closed is True


def test_read_accepts_numeric_channel_strings():
    make, made = _client_factory(_channels())
    assert len(_client(make).read("9", limit=1)["messages"]) == 1
    assert ("fetch_channel", 9) in made[0].calls


def test_send_maps_channel_and_text():
    make, made = _client_factory(_channels())
    result = _client(make).send(9, "hello")
    assert result == {"id": "501", "channel_id": "9", "content": "hello"}
    assert made[0].calls == [("login", "dc-secret"), ("fetch_channel", 9)]
    assert made[0].closed is True


def test_bad_arguments_are_value_errors():
    make, _ = _client_factory(_channels())
    client = _client(make)
    with pytest.raises(ValueError, match="channel_id must be a channel id"):
        client.read("general")
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        client.read(9, limit=101)
    with pytest.raises(ValueError, match="text must be a non-empty string"):
        client.send(9, "")
    with pytest.raises(ValueError, match="channel_id must be a channel id"):
        client.send(True, "hi")


def test_registry_reports_argument_errors_and_gates_sends():
    make, _ = _client_factory(_channels())
    log = ApprovalLog()
    registry = ToolRegistry(approval_log=log)
    register_discord_tools(registry, _client(make))

    assert (
        len(
            json.loads(registry.dispatch("discord_read", {"channel_id": 9}))["messages"]
        )
        == 2
    )
    assert "error" in json.loads(
        registry.dispatch("discord_send", {"channel_id": 9, "text": ""})
    )
    assert json.loads(
        registry.dispatch("discord_send", {"channel_id": 9, "text": "hi"})
    ) == {
        "error": "approval required",
        "tool": "discord_send",
    }
    assert log.approve("discord_send", "ada").get("approved") is True
    assert (
        json.loads(registry.dispatch("discord_send", {"channel_id": 9, "text": "hi"}))[
            "content"
        ]
        == "hi"
    )


def test_brokered_token_flows_and_refused_host_runs_nothing():
    make, made = _client_factory(_channels())
    broker = CredentialBroker(
        _policy(["discord.com"]), {"DISCORD_BOT_TOKEN": "dc-live"}
    )
    client = DiscordClient(make).with_broker(broker)
    assert len(client.read(9)["messages"]) == 2
    assert made[0].calls[0] == ("login", "dc-live")

    denied = CredentialBroker(_policy([]), {"DISCORD_BOT_TOKEN": "dc-live"})
    blocked = DiscordClient(make).with_broker(denied)
    calls_before = len(made)
    with pytest.raises(ProviderError, match="no credential for host"):
        blocked.read(9)
    assert len(made) == calls_before


def test_blank_token_is_refused_before_any_peer_call():
    make, made = _client_factory(_channels())
    with pytest.raises(DiscordError, match="no Discord credential"):
        DiscordClient(make, token="").read(9)
    assert made == []


def test_library_failures_name_the_operation():
    class _LibraryBoom(Exception):
        pass

    class ExplodingClient(FakeDiscordClient):
        async def login(self, token: str):
            raise _LibraryBoom("boom")

    def make() -> FakeDiscordClient:
        return ExplodingClient(_channels())

    with pytest.raises(DiscordError, match="discord read channel"):
        DiscordClient(make, token="dc-secret").read(9)


def test_default_factory_builds_a_real_client():
    pytest.importorskip("discord")
    assert discord is not None
    assert isinstance(DiscordClient().make_client(), discord.Client)


def test_default_client_names_missing_library(monkeypatch):
    import omes.tools.discord as tools_discord

    monkeypatch.setattr(tools_discord, "discord", None)
    with pytest.raises(DiscordError, match="not importable"):
        tools_discord._default_client()
