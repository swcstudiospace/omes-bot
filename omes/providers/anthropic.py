"""Anthropic messages wire: system extraction, content blocks, tool_use."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from omes.providers.base import Provider, ProviderError

ANTHROPIC_VERSION = "2023-06-01"


@dataclass
class AnthropicProvider(Provider):
    """POST ``{base_url}/v1/messages`` with an x-api-key header."""

    name: str = "anthropic"
    base_url: str = "https://api.anthropic.com"
    env_vars: tuple = ("ANTHROPIC_API_KEY",)
    api_mode: str = "messages"

    def build_request(
        self, model: str, messages: list, tools: Any, api_key: str
    ) -> tuple[str, dict, dict]:
        url = self.base_url.rstrip("/") + "/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        system, wire = to_anthropic_messages(messages)
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "messages": wire,
        }
        if system:
            body["system"] = system
        wire_tools = to_anthropic_tools(tools)
        if wire_tools is not None:
            body["tools"] = wire_tools
        return url, headers, body

    def parse_response(self, payload: dict) -> dict:
        blocks = payload.get("content")
        if not isinstance(blocks, list) or not blocks:
            raise ProviderError(f"{self.name} response has no content blocks")
        texts: list[str] = []
        calls: list[dict] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "text":
                texts.append(_text(block.get("text")))
            elif kind == "tool_use":
                name = block.get("name")
                if not name:
                    raise ProviderError(f"{self.name} tool_use has no name")
                calls.append(
                    {
                        "id": str(block.get("id", "")),
                        "type": "function",
                        "function": {
                            "name": str(name),
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    }
                )
        if not texts and not calls:
            raise ProviderError(f"{self.name} response has no usable content")
        row: dict[str, Any] = {"role": "assistant", "content": "\n".join(texts)}
        if calls:
            row["tool_calls"] = calls
        stop = payload.get("stop_reason")
        if stop:
            row["finish_reason"] = str(stop)
        return row


def to_anthropic_messages(messages: list) -> tuple[str, list[dict]]:
    """Split system rows out; map the rest to user/assistant turns."""
    system_parts: list[str] = []
    wire: list[dict] = []
    for row in messages:
        if not isinstance(row, dict):
            continue
        role = row.get("role", "user")
        if role == "system":
            system_parts.append(_text(row.get("content")))
            continue
        if role == "tool":
            block: dict[str, Any] = {
                "type": "tool_result",
                "content": _text(row.get("content")),
            }
            call_id = row.get("tool_call_id")
            if isinstance(call_id, str) and call_id:
                block["tool_use_id"] = call_id
            wire.append({"role": "user", "content": [block]})
            continue
        if role == "assistant":
            blocks: list[dict] = []
            text = _text(row.get("content"))
            if text:
                blocks.append({"type": "text", "text": text})
            calls = row.get("tool_calls")
            if isinstance(calls, list):
                for call in calls:
                    if not isinstance(call, dict):
                        continue
                    function = call.get("function")
                    if not isinstance(function, dict) or not function.get("name"):
                        continue
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": str(call.get("id", "")),
                            "name": str(function["name"]),
                            "input": _arguments(function.get("arguments")),
                        }
                    )
            wire.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
            continue
        wire.append({"role": "user", "content": _text(row.get("content"))})
    return "\n".join(system_parts), wire


def to_anthropic_tools(tools: Any) -> list | None:
    """Map the loop's tool map to Anthropic tools. None stays None."""
    if tools is None:
        return None
    if isinstance(tools, list):
        return tools
    if isinstance(tools, dict):
        return [
            {
                "name": str(name),
                "input_schema": {"type": "object", "properties": {}},
            }
            for name in tools
        ]
    return None


def _arguments(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


__all__ = ["ANTHROPIC_VERSION", "AnthropicProvider", "to_anthropic_messages", "to_anthropic_tools"]
