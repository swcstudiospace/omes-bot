"""Ollama wire: local /api/chat, no key, no streaming."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from omes.providers.base import Provider, ProviderError
from omes.providers.openai import normalize_tool_call, to_openai_messages, to_openai_tools


@dataclass
class OllamaProvider(Provider):
    """POST ``{base_url}/api/chat`` with ``stream: False``."""

    name: str = "ollama"
    base_url: str = "http://localhost:11434"
    env_vars: tuple = ()
    api_mode: str = "chat"
    requires_key: bool = False

    def build_request(
        self, model: str, messages: list, tools: Any, api_key: str
    ) -> tuple[str, dict, dict]:
        url = self.base_url.rstrip("/") + "/api/chat"
        body: dict[str, Any] = {
            "model": model,
            "messages": to_openai_messages(messages),
            "stream": False,
        }
        wire_tools = to_openai_tools(tools)
        if wire_tools is not None:
            body["tools"] = wire_tools
        return url, {"Content-Type": "application/json"}, body

    def parse_response(self, payload: dict) -> dict:
        message = payload.get("message")
        if not isinstance(message, dict):
            raise ProviderError(f"{self.name} response has no message")
        row: dict[str, Any] = {
            "role": "assistant",
            "content": _text(message.get("content")),
        }
        calls = message.get("tool_calls")
        if isinstance(calls, list) and calls:
            row["tool_calls"] = [normalize_tool_call(call) for call in calls]
        if not row["content"] and "tool_calls" not in row:
            raise ProviderError(f"{self.name} response has no usable content")
        return row


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


__all__ = ["OllamaProvider"]
