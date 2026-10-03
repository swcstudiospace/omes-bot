"""Phase 12: the provider contract, five adapters, the install surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from omes.agent.conversation_loop import Agent, run_conversation
from omes.agent.model import ScriptedModel
from omes.assemble import assembled_path, render, template_gaps
from omes.providers.anthropic import AnthropicProvider
from omes.providers.base import ProviderError, ProviderModel
from omes.providers.fake import FakeTransport
from omes.providers.gemini import GeminiProvider
from omes.providers.fake import FakeTransport
from omes.providers.grok import XAI_DEFAULT_BASE_URL, GrokProvider
from omes.providers.ollama import OllamaProvider
from omes.providers.openai import OpenAIProvider
from omes.receipts import ReceiptError, validate_receipt
from omes.tools.coding import CODING_TOOL_NAMES, register_coding_tools
from omes.tools.delegate import DELEG_TOOL_NAMES, register_delegate_tools
from omes.tools.discord import DISCORD_TOOL_NAMES, DiscordClient, register_discord_tools
from omes.tools.growth import GROWTH_TOOL_NAMES, register_growth_tools
from omes.tools.ide import IDE_TOOL_NAMES, register_ide_tools
from omes.tools.offer import offered_schemas
from omes.tools.platform import PLATFORM_TOOL_NAMES, register_platform_tools
from omes.tools.registry import ToolRegistry
from omes.tools.telegram import TELEGRAM_TOOL_NAMES, TelegramClient, register_telegram_tools
from omes.tools.lead import LEAD_TOOL_NAMES, LeadClient, LeadContext, register_lead_tools
from omes.tools.systems import SYS_TOOL_NAMES, SystemsClient, SystemsContext, register_systems_tools
from omes.tools.webpack import WEB_TOOL_NAMES, WebClient, WebContext, register_web_tools
from omes.tools.mobile import MOBILE_TOOL_NAMES, MobileClient, MobileContext, register_mobile_tools
from omes.tools.infra import INFRA_TOOL_NAMES, InfraClient, InfraContext, register_infra_tools
from omes.tools.packs import PACKS_TOOL_NAMES, PacksClient, PacksContext, register_packs_tools
from omes.tools.quality import QUALITY_TOOL_NAMES, QualityClient, QualityContext, register_quality_tools
from omes.substrate.client import SubstrateClient
from omes.tools.substrate_tools import SUBSTRATE_TOOL_NAMES, register_substrate_tools
from omes.tools.ultrathink import ULT_TOOL_NAMES, UltrathinkClient, UltrathinkContext, register_ultrathink_tools
from omes.tools.x import X_TOOL_NAMES, XClient, register_x_tools

OMES = Path(__file__).resolve().parents[1]
ROSTER = OMES / "contracts" / "tool-rosters" / "omes.yaml"


def test_fake_transport_completes_a_turn_through_the_contract():
    transport = FakeTransport(
        script=[{"choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}]}]
    )
    model = ProviderModel(GrokProvider(), "grok-4", transport, api_key="fake-key")
    agent = Agent(model=model, tools={}, max_iterations=4)
    result = run_conversation(agent, "ping", system_message="sys")

    assert result["final_response"] == "hello"
    assert len(transport.calls) == 1
    method, url, headers, body = transport.calls[0]
    assert url == XAI_DEFAULT_BASE_URL + "/chat/completions"
    assert headers["Authorization"] == "Bearer fake-key"
    assert body["model"] == "grok-4"
    assert body["messages"][0]["role"] == "system"
    assert "sys" in body["messages"][0]["content"]


def test_grok_adapter_round_trips_a_tool_call_and_needs_a_key():
    transport = FakeTransport(
        script=[
            {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "read_file",
                                        "arguments": '{"path": "x"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            }
        ]
    )
    model = ProviderModel(GrokProvider(), "grok-4", transport, api_key="fake-key")
    row = model.complete([{"role": "user", "content": "read"}], {"read_file": lambda: ""})

    assert row["role"] == "assistant"
    assert row["tool_calls"][0]["function"]["name"] == "read_file"
    assert row["finish_reason"] == "tool_calls"
    assert transport.calls[0][3]["tools"][0]["function"]["name"] == "read_file"

    keyless = ProviderModel(GrokProvider(), "grok-4", transport, api_key="")
    with pytest.raises(ProviderError, match="needs an API key"):
        keyless.complete([{"role": "user", "content": "x"}])
    assert len(transport.calls) == 1


def test_openai_adapter_answers_the_contract():
    transport = FakeTransport(
        script=[{"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}]
    )
    model = ProviderModel(OpenAIProvider(), "gpt-5", transport, api_key="fake-key")
    row = model.complete([{"role": "user", "content": "hi"}])

    assert row == {"role": "assistant", "content": "ok", "finish_reason": "stop"}
    method, url, headers, body = transport.calls[0]
    assert url == "https://api.openai.com/v1/chat/completions"
    assert headers["Authorization"] == "Bearer fake-key"
    assert "tools" not in body


def test_anthropic_adapter_answers_the_contract():
    transport = FakeTransport(
        script=[
            {
                "content": [
                    {"type": "text", "text": "reading"},
                    {
                        "type": "tool_use",
                        "id": "tu-1",
                        "name": "read_file",
                        "input": {"path": "x"},
                    },
                ],
                "stop_reason": "tool_use",
            }
        ]
    )
    model = ProviderModel(AnthropicProvider(), "claude-1", transport, api_key="fake-key")
    row = model.complete(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "read x"},
        ]
    )

    assert row["content"] == "reading"
    assert row["tool_calls"] == [
        {
            "id": "tu-1",
            "type": "function",
            "function": {"name": "read_file", "arguments": '{"path": "x"}'},
        }
    ]
    method, url, headers, body = transport.calls[0]
    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == "fake-key"
    assert headers["anthropic-version"] == "2023-06-01"
    assert body["system"] == "sys"
    assert body["messages"] == [{"role": "user", "content": "read x"}]


def test_gemini_adapter_answers_the_contract():
    transport = FakeTransport(
        script=[
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"functionCall": {"name": "read_file", "args": {"path": "x"}}}
                            ]
                        }
                    }
                ]
            }
        ]
    )
    model = ProviderModel(GeminiProvider(), "gemini-3", transport, api_key="fake-key")
    row = model.complete([{"role": "user", "content": "read x"}])

    assert row["tool_calls"][0]["function"]["name"] == "read_file"
    assert json.loads(row["tool_calls"][0]["function"]["arguments"]) == {"path": "x"}
    method, url, headers, body = transport.calls[0]
    assert url == (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3:generateContent"
    )
    assert headers["x-goog-api-key"] == "fake-key"
    assert body["contents"][0]["role"] == "user"


def test_ollama_adapter_answers_the_contract_without_a_key():
    transport = FakeTransport(
        script=[
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-9",
                            "type": "function",
                            "function": {"name": "read_file", "arguments": {"path": "x"}},
                        }
                    ],
                }
            }
        ]
    )
    model = ProviderModel(OllamaProvider(), "qwen3", transport)
    row = model.complete([{"role": "user", "content": "read x"}])

    assert row["tool_calls"][0]["id"] == "call-9"
    method, url, headers, body = transport.calls[0]
    assert url == "http://localhost:11434/api/chat"
    assert "Authorization" not in headers
    assert body["stream"] is False

    empty = ProviderModel(
        OllamaProvider(), "qwen3", FakeTransport(script=[{"message": {"role": "x"}}])
    )
    with pytest.raises(ProviderError):
        empty.complete([{"role": "user", "content": "x"}])


def _roster_names(text: str) -> list[str]:
    names: list[str] = []
    in_tools = False
    for line in text.splitlines():
        if line.startswith("tools:"):
            in_tools = True
            continue
        if not in_tools:
            continue
        if line.startswith("  - "):
            names.append(line[4:].strip())
            continue
        if line.strip() and not line.startswith("#") and not line.startswith(" "):
            break
    return names


def test_install_surface_names_only_what_exists(tmp_path: Path):
    registry = ToolRegistry()
    register_coding_tools(registry, tmp_path)
    register_growth_tools(
        registry,
        skills_root=tmp_path / "skills",
        memory_dir=tmp_path / "memory",
        session_db=tmp_path / "sessions.db",
    )
    register_delegate_tools(registry, Agent(model=ScriptedModel([]), tools={}))
    register_platform_tools(registry, home=tmp_path)
    register_ide_tools(registry, tmp_path)
    register_x_tools(registry, XClient(FakeTransport(), token="fake"))
    register_telegram_tools(
        registry, TelegramClient(make_bot=lambda token: None, token="fake")
    )
    register_discord_tools(registry, DiscordClient(make_client=lambda: None, token="fake"))
    register_lead_tools(registry, LeadClient(LeadContext(root=tmp_path)))
    register_systems_tools(registry, SystemsClient(SystemsContext(root=tmp_path)))
    register_web_tools(registry, WebClient(WebContext(root=tmp_path)))
    register_mobile_tools(registry, MobileClient(MobileContext(root=tmp_path)))
    register_infra_tools(registry, InfraClient(InfraContext()))
    register_quality_tools(registry, QualityClient(QualityContext(root=tmp_path)))
    register_packs_tools(registry, PacksClient(PacksContext()))
    register_ultrathink_tools(registry, UltrathinkClient(UltrathinkContext()))
    register_substrate_tools(registry, SubstrateClient())

    roster = _roster_names(ROSTER.read_text(encoding="utf-8"))
    assert roster == list(
        CODING_TOOL_NAMES
        + GROWTH_TOOL_NAMES
        + DELEG_TOOL_NAMES
        + PLATFORM_TOOL_NAMES
        + IDE_TOOL_NAMES
        + X_TOOL_NAMES
        + TELEGRAM_TOOL_NAMES
        + DISCORD_TOOL_NAMES
        + LEAD_TOOL_NAMES
        + SYS_TOOL_NAMES
        + WEB_TOOL_NAMES
        + MOBILE_TOOL_NAMES
        + INFRA_TOOL_NAMES
        + QUALITY_TOOL_NAMES
        + PACKS_TOOL_NAMES
        + ULT_TOOL_NAMES
        + SUBSTRATE_TOOL_NAMES
    )
    offered = offered_schemas(registry, roster)
    assert [item["function"]["name"] for item in offered] == roster

    assert template_gaps(OMES) == []
    assert (
        assembled_path(OMES).read_text(encoding="utf-8")
        == render(OMES, OMES / "grokbot" / "rosters" / "default.json")
    )

    with pytest.raises(ReceiptError):
        validate_receipt(
            {
                "commands": [{"cmd": "true", "exit_code": 0}],
                "claims": [{"claim": "done", "evidence_command_index": 5}],
                "unverified": [],
            }
        )
    validate_receipt(
        {
            "commands": [{"cmd": "python3 -m pytest omes/tests -q", "exit_code": 0}],
            "claims": [{"claim": "suite passes", "evidence_command_index": 0}],
            "unverified": [],
        }
    )
