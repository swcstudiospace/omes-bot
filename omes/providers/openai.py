"""OpenAI chat-completions wire. Grok subclasses this: xAI speaks it too."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from omes.providers.base import Provider, ProviderError


@dataclass
class OpenAIProvider(Provider):
    """POST ``{base_url}/chat/completions`` with a Bearer [SECURITY_DATA]"""

    name: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    env_vars: tuple = ("OPENAI_API_KEY",)
    api_mode: str = "chat_completions"

    def build_request(
        self, model: str, messages: list, tools: Any, api_key: str
    ) -> tuple[str, dict, dict]:
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": model,
            "messages": to_openai_messages(messages),
        }
        wire_tools = to_openai_tools(tools)
        if wire_tools is not None:
            body["tools"] = wire_tools
        return url, headers, body

    def parse_response(self, payload: dict) -> dict:
        try:
            choices = payload["choices"]
            first = choices[0]
            message = first["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.name} response has no message: {exc}") from exc
        if not isinstance(message, dict):
            raise ProviderError(f"{self.name} response message is not an object")
        row: dict[str, Any] = {
            "role": "assistant",
            "content": _text(message.get("content")),
        }
        calls = message.get("tool_calls")
        if isinstance(calls, list) and calls:
            row["tool_calls"] = [normalize_tool_call(call) for call in calls]
        finish = first.get("finish_reason") if isinstance(first, dict) else None
        if finish:
            row["finish_reason"] = str(finish)
        return row

    def parse_usage(self, payload: dict) -> dict[str, int] | None:
        return self._usage_from(
            payload,
            "usage",
            (
                ("prompt_tokens", "prompt_tokens"),
                ("completion_tokens", "completion_tokens"),
                ("total_tokens", "total_tokens"),
            ),
        )


def to_openai_messages(messages: list) -> list[dict]:
    """Map transcript rows to chat-completions messages."""
    wire: list[dict] = []
    for row in messages:
        if not isinstance(row, dict):
            continue
        role = row.get("role", "user")
        if role == "tool":
            item: dict[str, Any] = {
                "role": "tool",
                "content": _text(row.get("content")),
            }
            call_id = row.get("tool_call_id")
            if isinstance(call_id, str) and call_id:
                item["tool_call_id"] = call_id
            wire.append(item)
            continue
        if role == "assistant":
            item = {"role": "assistant", "content": _text(row.get("content"))}
            calls = row.get("tool_calls")
            if isinstance(calls, list) and calls:
                item["tool_calls"] = [normalize_tool_call(call) for call in calls]
            wire.append(item)
            continue
        wire.append({"role": str(role), "content": _text(row.get("content"))})
    return wire


def to_openai_tools(tools: Any) -> list | None:
    """Map the loop's tool map to chat-completions tools. None stays None."""
    if tools is None:
        return None
    if isinstance(tools, list):
        return tools
    if isinstance(tools, dict):
        return [
            {
                "type": "function",
                "function": {
                    "name": str(name),
                    "parameters": {"type": "object", "properties": {}},
                },
            }
            for name in tools
        ]
    return None


def normalize_tool_call(call: Any) -> dict:
    """One ``{"id", "type", "function": {"name", "arguments"}}`` call."""
    if not isinstance(call, dict):
        raise ProviderError(f"tool call is not an object: {call!r}")
    function = call.get("function")
    if not isinstance(function, dict) or not function.get("name"):
        raise ProviderError(f"tool call has no function name: {call!r}")
    arguments = function.get("arguments", {})
    if isinstance(arguments, dict) or not isinstance(arguments, str):
        arguments = json.dumps(arguments)
    return {
        "id": str(call.get("id", "")),
        "type": "function",
        "function": {"name": str(function["name"]), "arguments": arguments},
    }


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


__all__ = [
    "OpenAIProvider",
    "normalize_tool_call",
    "to_openai_messages",
    "to_openai_tools",
]
