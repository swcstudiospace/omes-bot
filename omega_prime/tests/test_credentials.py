"""Phase 14: brokered credentials and secret redaction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omega_prime.agent.conversation_loop import Agent, run_conversation
from omega_prime.agent.harness import emit, events_of
from omega_prime.audit.log import AuditLog
from omega_prime.credentials.broker import CredentialBroker
from omega_prime.credentials.redact import REDACTED, redact_text
from omega_prime.memory.provider import BuiltinMemoryProvider
from omega_prime.memory.store import MemoryStore
from omega_prime.policy.policy import SeatPolicy
from omega_prime.providers.base import ProviderError, ProviderModel
from omega_prime.providers.fake import FakeTransport
from omega_prime.providers.grok import GrokProvider


def _policy(hosts: list[str]) -> SeatPolicy:
    return SeatPolicy(
        {"version": 1, "tools": {}, "paths": {}, "network": {"hosts": hosts}}
    )


def test_broker_injects_the_key_the_agent_never_handles():
    broker = CredentialBroker(
        _policy(["api.x.ai"]), {"XAI_API_KEY": "xai-secret-value"}
    )
    transport = FakeTransport(
        script=[{"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}]}]
    )
    model = ProviderModel(GrokProvider(), "grok-4", transport, broker=broker)
    agent = Agent(model=model, tools={}, max_iterations=2)
    result = run_conversation(agent, "ping")

    assert result["final_response"] == "hi"
    _method, url, headers, _body = transport.calls[0]
    assert url == "https://api.x.ai/v1/chat/completions"
    assert headers["Authorization"] == "Bearer xai-secret-value"
    assert model.api_key == ""
    scrubbed = broker.redact(json.dumps(headers))
    assert "xai-secret-value" not in scrubbed
    assert REDACTED in scrubbed


def test_broker_refuses_without_a_key_and_without_a_transport_call():
    broker = CredentialBroker(_policy(["api.x.ai"]), {})
    transport = FakeTransport(
        script=[{"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}]}]
    )
    model = ProviderModel(GrokProvider(), "grok-4", transport, broker=broker)

    with pytest.raises(ProviderError, match="XAI_API_KEY"):
        model.complete([{"role": "user", "content": "ping"}])
    assert transport.calls == []


def test_broker_withholds_credentials_from_unapproved_hosts():
    broker = CredentialBroker(
        _policy(["api.x.ai"]), {"XAI_API_KEY": "xai-secret-value"}
    )

    with pytest.raises(ProviderError, match=r"evil\.example"):
        broker.key_for(GrokProvider(), "https://evil.example/v1/chat/completions")
    assert broker.key_for(GrokProvider(), "https://API.X.AI/v1/chat/completions") == (
        "xai-secret-value"
    )

    transport = FakeTransport(script=[{"choices": [{"message": {"content": "x"}}]}])
    model = ProviderModel(GrokProvider(), "grok-4", transport, broker=broker)
    evil = GrokProvider()
    evil.base_url = "https://evil.example/v1"
    evil_model = ProviderModel(evil, "grok-4", transport, broker=broker)
    with pytest.raises(ProviderError, match="no credential for host"):
        evil_model.complete([{"role": "user", "content": "ping"}])
    assert transport.calls == []
    assert model.complete([{"role": "user", "content": "ping"}])["content"] == "x"


def test_redact_text_covers_keys_tokens_and_assignments():
    assert redact_text("key sk-abcdefgh1234 end") == f"key {REDACTED} end"
    assert redact_text("tok xai-abcdef123456 end") == f"tok {REDACTED} end"
    assert redact_text("tok ghp_abcdefgh1234 end") == f"tok {REDACTED} end"
    assert redact_text("auth Bearer abcdef123 end") == f"auth Bearer {REDACTED} end"
    assert redact_text('api_key="hunter2-abcdef" ok') == f'api_key="{REDACTED}" ok'
    assert redact_text("token: hunter2-abcdef ok") == f"token: {REDACTED} ok"
    assert redact_text("nothing secret here") == "nothing secret here"
    assert redact_text(None) is None
    assert redact_text(42) == 42
    assert (
        redact_text("see hunter2-abcdef!", extra=("hunter2-abcdef",))
        == f"see {REDACTED}!"
    )


def test_audit_events_and_recall_store_redacted(tmp_path: Path):
    log = AuditLog(tmp_path / "audit.ndjson")
    log.append("read_file", "error", "boom sk-testkey123")
    record = log.records()[0]
    assert record["reason"] == f"boom {REDACTED}"
    assert "sk-testkey123" not in (tmp_path / "audit.ndjson").read_text(
        encoding="utf-8"
    )

    class Bag:
        pass

    bag = Bag()
    emit(bag, "note", detail="token ghp_abcdefgh1234")
    assert events_of(bag)[0]["detail"] == f"token {REDACTED}"

    store = MemoryStore(tmp_path / "mem")
    store.add("memory", "deploy with sk-testkey123")
    provider = BuiltinMemoryProvider(store)
    recalled = provider.prefetch("deploy?")
    assert "sk-testkey123" not in recalled
    assert REDACTED in recalled
    assert store.render() != recalled
