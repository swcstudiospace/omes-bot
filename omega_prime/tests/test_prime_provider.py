# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Consumer-visible Prime translation, replay, credentials, and loop tests.

The native boundary is deterministic here; localhost provider HTTP is covered
by the native integration suite, not replaced by a product fallback.
"""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from omega_prime.agent import OmegaPrimeAgent
from omega_prime.credentials.broker import CredentialBroker
from omega_prime.providers import prime
from omega_prime.providers.base import ProviderError
from omega_prime.providers.prime import PrimeProviderModel
from omega_prime.tools.registry import ToolRegistry

MODEL = {
    "id": "test-model",
    "name": "Test model",
    "api": "openai-completions",
    "provider": "openai",
    "baseUrl": "https://api.openai.com/v1",
    "reasoning": True,
    "input": ["text", "image"],
    "cost": {"input": 1, "output": 2, "cacheRead": 0.1, "cacheWrite": 1},
    "contextWindow": 8192,
    "maxTokens": 1024,
    "compat": {"supportsDeveloperRole": False},
}
SCHEMA: dict = {
    "type": "function",
    "function": {
        "name": "lookup",
        "description": "Look up a record by its identifier.",
        "parameters": {
            "type": "object",
            "properties": {"identifier": {"type": "string"}},
            "required": ["identifier"],
        },
    },
}


def _reply(content=None, **fields):
    return {
        "role": "assistant",
        "content": content
        if content is not None
        else [{"type": "text", "text": "done"}],
        "api": MODEL["api"],
        "provider": MODEL["provider"],
        "model": MODEL["id"],
        "responseId": "response-1",
        "responseModel": "concrete-model",
        "usage": {
            "input": 10,
            "output": 3,
            "cacheRead": 4,
            "cacheWrite": 2,
            "totalTokens": 19,
            "cost": {
                "input": 0,
                "output": 0,
                "cacheRead": 0,
                "cacheWrite": 0,
                "total": 0,
            },
        },
        "stopReason": "stop",
        "timestamp": 123,
        **fields,
    }


class _Native:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, model, context, options):
        self.calls.append(copy.deepcopy((model, context, options)))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return copy.deepcopy(reply)


@pytest.fixture
def native(monkeypatch):
    def install(*replies):
        boundary = _Native(replies)
        monkeypatch.setattr(
            prime, "load_extension", lambda: SimpleNamespace(ai=boundary)
        )
        return boundary

    return install


def test_text_system_options_and_usage(native):
    boundary = native(_reply())
    model = PrimeProviderModel(
        MODEL, api_key="secret", options={"reasoning": "high", "maxTokens": 128}
    )
    messages = [
        {"role": "system", "content": "first"},
        {"role": "system", "content": [{"type": "text", "text": "second"}]},
        {"role": "user", "content": "hello", "timestamp": 42},
    ]
    original = copy.deepcopy(messages)
    row = model.complete(messages)
    descriptor, context, options = boundary.calls[0]
    assert descriptor == MODEL
    assert context == {
        "systemPrompt": "first\nsecond",
        "messages": [{"role": "user", "content": "hello", "timestamp": 42}],
    }
    assert options == {"reasoning": "high", "maxTokens": 128, "apiKey": "secret"}
    assert row["content"] == "done"
    assert row["finish_reason"] == "stop"
    assert model.last_usage == {
        "prompt_tokens": 16,
        "completion_tokens": 3,
        "total_tokens": 19,
        "cache_read_tokens": 4,
        "cache_write_tokens": 2,
    }
    assert messages == original


def test_tool_thinking_and_response_metadata_survive_json_replay(native):
    reply = _reply(
        [
            {"type": "thinking", "thinking": "reason", "thinkingSignature": "opaque"},
            {"type": "text", "text": "working", "textSignature": "text-id"},
            {
                "type": "toolCall",
                "id": "call-1",
                "name": "lookup",
                "arguments": {"identifier": "記録"},
                "thoughtSignature": "google-opaque",
            },
        ],
        stopReason="toolUse",
        diagnostics=[{"type": "test", "timestamp": 123}],
    )
    boundary = native(reply, _reply())
    model = PrimeProviderModel(MODEL, api_key="secret")
    row = model.complete([{"role": "user", "content": "find"}], [SCHEMA])
    assert row["thinking"] == "reason"
    assert row["finish_reason"] == "tool_calls"
    assert json.loads(row["tool_calls"][0]["function"]["arguments"]) == {
        "identifier": "記録"
    }
    restored = json.loads(json.dumps(row))
    model.complete(
        [
            {"role": "user", "content": "find"},
            restored,
            {"role": "tool", "tool_call_id": "call-1", "content": '{"answer": 7}'},
        ],
        [SCHEMA],
    )
    context = boundary.calls[1][1]
    assert context["messages"][1] == reply
    assert context["messages"][2]["toolName"] == "lookup"
    assert context["messages"][2]["content"] == [
        {"type": "text", "text": '{"answer": 7}'}
    ]
    assert context["messages"][2]["isError"] is False
    assert context["tools"] == [SCHEMA["function"]]


def test_historical_omega_tool_calls_are_json_objects(native):
    boundary = native(_reply())
    PrimeProviderModel(MODEL, api_key="secret").complete(
        [
            {
                "role": "assistant",
                "content": "working",
                "thinking": "reason",
                "thinking_signature": "sig",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {
                            "name": "lookup",
                            "arguments": '{"identifier":"x"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "name": "lookup",
                "tool_call_id": "call-1",
                "content": "error: missing",
                "details": {"status": 404},
            },
        ]
    )
    assistant, result = boundary.calls[0][1]["messages"]
    assert assistant["content"][0] == {
        "type": "thinking",
        "thinking": "reason",
        "thinkingSignature": "sig",
    }
    assert assistant["content"][-1]["arguments"] == {"identifier": "x"}
    assert assistant["stopReason"] == "toolUse"
    assert result["isError"] is True
    assert result["details"] == {"status": 404}


@pytest.mark.parametrize(
    "image",
    [
        {"type": "image", "data": "YWJj", "mimeType": "image/png"},
        {
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64,YWJj"},
        },
        {
            "type": "image",
            "source": {"type": "base64", "data": "YWJj", "media_type": "image/png"},
        },
        {"inlineData": {"data": "YWJj", "mimeType": "image/png"}},
    ],
)
def test_embedded_images_remain_real_prime_image_blocks(native, image):
    boundary = native(_reply())
    PrimeProviderModel(MODEL, api_key="secret").complete(
        [{"role": "user", "content": [{"type": "text", "text": "see"}, image]}]
    )
    assert boundary.calls[0][1]["messages"][0]["content"] == [
        {"type": "text", "text": "see"},
        {"type": "image", "data": "YWJj", "mimeType": "image/png"},
    ]


def test_remote_images_are_not_silently_fetched_or_dropped(native):
    boundary = native(_reply())
    with pytest.raises(ProviderError, match="remote URLs are not fetched"):
        PrimeProviderModel(MODEL, api_key="secret").complete(
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": "https://example.org/a.png"},
                        }
                    ],
                }
            ]
        )
    assert boundary.calls == []


@pytest.mark.parametrize("stop", ["error", "aborted"])
def test_terminal_failure_raises_and_clears_stale_usage(native, stop):
    boundary = native(
        _reply(), _reply(stopReason=stop, errorMessage="provider denied secret")
    )
    model = PrimeProviderModel(MODEL, api_key="secret")
    model.complete([])
    assert model.last_usage is not None
    with pytest.raises(ProviderError, match=f"Prime {stop}") as error:
        model.complete([])
    assert "secret" not in str(error.value)
    assert "[REDACTED]" in str(error.value)
    assert model.last_usage is None
    assert error.value.__cause__ is None
    assert len(boundary.calls) == 2


@pytest.mark.parametrize("missing_ai", [False, True])
def test_missing_extension_or_ai_is_explicit_error(monkeypatch, missing_ai):
    def missing():
        if missing_ai:
            return SimpleNamespace()
        raise ImportError("no binary")

    monkeypatch.setattr(prime, "load_extension", missing)
    with pytest.raises(ProviderError, match=r"native ai\.complete is unavailable"):
        PrimeProviderModel(MODEL, api_key="secret").complete([])


def test_missing_key_is_refused_before_native_loading(monkeypatch):
    def forbidden():
        raise AssertionError("native dispatch must not occur")

    monkeypatch.setattr(prime, "load_extension", forbidden)
    with pytest.raises(ProviderError, match="needs an API key"):
        PrimeProviderModel(MODEL).complete([])


def test_options_key_is_supported_but_explicit_key_wins(native):
    boundary = native(_reply(), _reply())
    PrimeProviderModel(MODEL, options={"apiKey": "options-key"}).complete([])
    PrimeProviderModel(
        MODEL, api_key="explicit", options={"apiKey": "options-key"}
    ).complete([])
    assert boundary.calls[0][2]["apiKey"] == "options-key"
    assert boundary.calls[1][2]["apiKey"] == "explicit"


def test_broker_approves_host_and_resolves_per_call(native):
    boundary = native(_reply(), _reply())
    env = {"OPENAI_API_KEY": "approved-1"}
    policy = SimpleNamespace(allows_host=lambda host: host == "api.openai.com")
    model = PrimeProviderModel(
        MODEL, api_key="ignored", broker=CredentialBroker(policy, env)
    )
    model.complete([])
    env["OPENAI_API_KEY"] = "approved-2"
    model.complete([])
    assert [call[2]["apiKey"] for call in boundary.calls] == [
        "approved-1",
        "approved-2",
    ]


def test_unapproved_broker_host_cannot_dispatch_even_with_explicit_key(native):
    boundary = native(_reply())
    broker = CredentialBroker(
        SimpleNamespace(allows_host=lambda host: False),
        {"OPENAI_API_KEY": "secret"},
    )
    with pytest.raises(ProviderError, match="no credential for host"):
        PrimeProviderModel(MODEL, api_key="explicit", broker=broker).complete([])
    assert boundary.calls == []


def test_plain_callable_tools_are_rejected_not_given_invented_schema(native):
    boundary = native(_reply())
    with pytest.raises(ProviderError, match="registered schemas"):
        PrimeProviderModel(MODEL, api_key="secret").complete(
            [], {"lookup": lambda identifier: identifier}
        )
    assert boundary.calls == []


@pytest.mark.parametrize("arguments", ["{bad", "[]", 123])
def test_invalid_tool_arguments_never_dispatch(native, arguments):
    boundary = native(_reply())
    with pytest.raises(ProviderError, match="tool arguments"):
        PrimeProviderModel(MODEL, api_key="secret").complete(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "function": {"name": "lookup", "arguments": arguments},
                        }
                    ],
                }
            ]
        )
    assert boundary.calls == []


def test_edited_rows_cannot_replay_stale_opaque_signatures(native):
    boundary = native(_reply(), _reply())
    model = PrimeProviderModel(MODEL, api_key="secret")
    row = model.complete([])
    row["content"] = "edited"
    with pytest.raises(ProviderError, match="metadata does not match"):
        model.complete([row])
    assert len(boundary.calls) == 1


@pytest.mark.parametrize(
    "reply",
    [
        None,
        {"role": "user", "content": "bad"},
        _reply(stopReason="unknown"),
        _reply([{"type": "unknown", "text": "bad"}]),
        _reply([{"type": "toolCall", "id": "x", "name": "lookup", "arguments": []}]),
    ],
)
def test_malformed_native_payload_is_provider_error(native, reply):
    boundary = native(reply)
    with pytest.raises(ProviderError):
        PrimeProviderModel(MODEL, api_key="secret").complete([])
    assert len(boundary.calls) == 1


def test_tool_errors_follow_omega_and_registry_representations(native):
    boundary = native(_reply())
    PrimeProviderModel(MODEL, api_key="secret").complete(
        [
            {
                "role": "tool",
                "name": "lookup",
                "tool_call_id": "1",
                "content": '{"error":"approval required"}',
            },
            {
                "role": "tool",
                "name": "lookup",
                "tool_call_id": "2",
                "content": "ordinary text",
                "is_error": True,
            },
            {
                "role": "tool",
                "name": "lookup",
                "tool_call_id": "3",
                "content": "error: overridden",
                "is_error": False,
            },
        ]
    )
    assert [row["isError"] for row in boundary.calls[0][1]["messages"]] == [
        True,
        True,
        False,
    ]


def test_composition_runs_real_loop_tool_round_and_replays_durable_metadata(native):
    tool_reply = _reply(
        [
            {"type": "thinking", "thinking": "find it", "thinkingSignature": "signed"},
            {
                "type": "toolCall",
                "id": "call-1",
                "name": "lookup",
                "arguments": {"identifier": "record-1"},
            },
        ],
        stopReason="toolUse",
    )
    text_reply = _reply(
        [{"type": "text", "text": "found", "textSignature": "final-signed"}],
        responseId="response-2",
    )
    boundary = native(tool_reply, text_reply, _reply())
    registry = ToolRegistry()
    function = SCHEMA["function"]
    executed = []

    def lookup(identifier):
        executed.append(identifier)
        return {"answer": 7}

    registry.register(
        function["name"], function["description"], function["parameters"], lookup
    )
    agent = OmegaPrimeAgent.from_prime(
        MODEL,
        registry=registry,
        api_key="secret",
        max_iterations=4,
        system_message="Use lookup.",
    )
    result = agent.run("Find record-1")
    assert result["final_response"] == "found"
    assert executed == ["record-1"]
    second_context = boundary.calls[1][1]
    assert second_context["tools"] == [function]
    assert second_context["messages"][-2] == tool_reply
    assert second_context["messages"][-1]["role"] == "toolResult"
    assert json.loads(second_context["messages"][-1]["content"][0]["text"]) == {
        "answer": 7
    }
    assert agent.messages[-1]["prime_message"] == text_reply
    # Session serialization and a fresh model must not lose opaque metadata.
    restored = json.loads(json.dumps(agent.messages))
    fresh_model = PrimeProviderModel(MODEL, api_key="secret")
    fresh_model.complete(restored, registry.schemas())
    assert boundary.calls[2][1]["messages"][-1] == text_reply


@pytest.mark.parametrize("field", ["id", "provider", "api", "baseUrl"])
def test_descriptor_is_required_not_a_provider_name(field):
    descriptor = {key: value for key, value in MODEL.items() if key != field}
    with pytest.raises(ProviderError, match=field):
        PrimeProviderModel(descriptor, api_key="secret")


@pytest.mark.parametrize(
    "tools",
    [
        [{"type": "function", "function": {"name": "lookup"}}],
        [{"name": "lookup", "parameters": {"type": "object"}, "description": 2}],
    ],
)
def test_incomplete_tool_definitions_are_errors_before_native_dispatch(native, tools):
    boundary = native(_reply())
    with pytest.raises(ProviderError, match="tool"):
        PrimeProviderModel(MODEL, api_key="secret").complete([], tools)
    assert boundary.calls == []


def test_length_finish_and_thinking_only_content_are_not_provider_errors(native):
    native(
        _reply(
            [
                {
                    "type": "thinking",
                    "thinking": "",
                    "thinkingSignature": "redacted",
                    "redacted": True,
                }
            ],
            stopReason="length",
        )
    )
    row = PrimeProviderModel(MODEL, api_key="secret").complete([])
    assert row["content"] == ""
    assert row["finish_reason"] == "length"
    assert row["prime_message"]["content"][0]["thinkingSignature"] == "redacted"


def test_malformed_usage_counters_are_not_claimed_as_tokens(native):
    native(_reply(usage={"input": True, "output": -1, "totalTokens": "19"}))
    model = PrimeProviderModel(MODEL, api_key="secret")
    model.complete([])
    assert model.last_usage is None
