"""Anthropic messages wire: system extraction, content blocks, tool_use."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from omega_prime.providers.base import Provider, ProviderError

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
            "max_tokens": 8192,
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

    def parse_usage(self, payload: dict) -> dict[str, int] | None:
        return self._usage_from(
            payload,
            "usage",
            (
                ("input_tokens", "prompt_tokens"),
                ("output_tokens", "completion_tokens"),
            ),
        )

    def parse_stream(self, lines: Any) -> tuple[dict[str, Any], dict[str, int] | None]:
        """Accumulate Anthropic SSE deltas into ``(row, usage?)``."""
        texts: list[str] = []
        calls: dict[int, dict[str, Any]] = {}
        usage: dict[str, int] = {}
        for event in self._sse_data(lines):
            kind = event.get("type")
            if kind == "message_start":
                message = event.get("message") or {}
                block = self._usage_from(
                    message if isinstance(message, dict) else {},
                    "usage",
                    (("input_tokens", "prompt_tokens"),),
                )
                if block is not None:
                    usage.update(block)
            elif kind == "content_block_start":
                block = event.get("content_block") or {}
                index = event.get("index", 0)
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_use"
                    and isinstance(index, int)
                ):
                    calls[index] = {
                        "id": str(block.get("id", "")),
                        "name": str(block.get("name", "")),
                        "arguments": "",
                    }
            elif kind == "content_block_delta":
                delta = event.get("delta") or {}
                index = event.get("index", 0)
                if not isinstance(delta, dict) or not isinstance(index, int):
                    continue
                if delta.get("type") == "text_delta":
                    piece = delta.get("text")
                    if isinstance(piece, str) and piece:
                        texts.append(piece)
                elif delta.get("type") == "input_json_delta":
                    piece = delta.get("partial_json")
                    if isinstance(piece, str) and index in calls:
                        calls[index]["arguments"] += piece
            elif kind == "message_delta":
                block = self._usage_from(
                    event,
                    "usage",
                    (("output_tokens", "completion_tokens"),),
                )
                if block is not None:
                    usage.update(block)
        row: dict[str, Any] = {"role": "assistant", "content": "".join(texts)}
        merged = [calls[index] for index in sorted(calls) if calls[index]["name"]]
        if merged:
            row["tool_calls"] = [
                {
                    "id": slot["id"],
                    "type": "function",
                    "function": {
                        "name": slot["name"],
                        "arguments": _arguments(slot["arguments"]),
                    },
                }
                for slot in merged
            ]
        return row, usage or None


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
            wire.append(
                {
                    "role": "assistant",
                    "content": blocks or [{"type": "text", "text": ""}],
                }
            )
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


__all__ = [
    "ANTHROPIC_VERSION",
    "AnthropicProvider",
    "to_anthropic_messages",
    "to_anthropic_tools",
]
