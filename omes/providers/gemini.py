"""Gemini wire: contents with parts, functionCall round-trips."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from omes.providers.base import Provider, ProviderError


@dataclass
class GeminiProvider(Provider):
    """POST ``{base_url}/models/{model}:generateContent``."""

    name: str = "gemini"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    env_vars: tuple = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    api_mode: str = "generate_content"

    def build_request(
        self, model: str, messages: list, tools: Any, api_key: str
    ) -> tuple[str, dict, dict]:
        url = self.base_url.rstrip("/") + f"/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }
        system, contents = to_gemini_contents(messages)
        body: dict[str, Any] = {"contents": contents}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        declarations = to_gemini_tools(tools)
        if declarations is not None:
            body["tools"] = [{"functionDeclarations": declarations}]
        return url, headers, body

    def parse_response(self, payload: dict) -> dict:
        try:
            candidates = payload["candidates"]
            content = candidates[0]["content"]
            parts = content["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.name} response has no parts: {exc}") from exc
        if not isinstance(parts, list) or not parts:
            raise ProviderError(f"{self.name} response has no parts")
        texts: list[str] = []
        calls: list[dict] = []
        for part in parts:
            if not isinstance(part, dict):
                continue
            if "text" in part:
                texts.append(_text(part.get("text")))
            call = part.get("functionCall")
            if isinstance(call, dict) and call.get("name"):
                calls.append(
                    {
                        "id": "",
                        "type": "function",
                        "function": {
                            "name": str(call["name"]),
                            "arguments": json.dumps(call.get("args", {})),
                        },
                    }
                )
        if not texts and not calls:
            raise ProviderError(f"{self.name} response has no usable content")
        row: dict[str, Any] = {"role": "assistant", "content": "\n".join(texts)}
        if calls:
            row["tool_calls"] = calls
        return row

    def parse_usage(self, payload: dict) -> dict[str, int] | None:
        return self._usage_from(
            payload,
            "usageMetadata",
            (
                ("promptTokenCount", "prompt_tokens"),
                ("candidatesTokenCount", "completion_tokens"),
                ("totalTokenCount", "total_tokens"),
            ),
        )


def to_gemini_contents(messages: list) -> tuple[str, list[dict]]:
    """Split system rows out; map the rest to user/model contents."""
    system_parts: list[str] = []
    contents: list[dict] = []
    for row in messages:
        if not isinstance(row, dict):
            continue
        role = row.get("role", "user")
        if role == "system":
            system_parts.append(_text(row.get("content")))
            continue
        if role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": str(row.get("name", "")),
                                "response": {"output": _text(row.get("content"))},
                            }
                        }
                    ],
                }
            )
            continue
        if role == "assistant":
            parts: list[dict] = []
            text = _text(row.get("content"))
            if text:
                parts.append({"text": text})
            calls = row.get("tool_calls")
            if isinstance(calls, list):
                for call in calls:
                    if not isinstance(call, dict):
                        continue
                    function = call.get("function")
                    if not isinstance(function, dict) or not function.get("name"):
                        continue
                    parts.append(
                        {
                            "functionCall": {
                                "name": str(function["name"]),
                                "args": _arguments(function.get("arguments")),
                            }
                        }
                    )
            contents.append({"role": "model", "parts": parts or [{"text": ""}]})
            continue
        contents.append(
            {"role": "user", "parts": [{"text": _text(row.get("content"))}]}
        )
    return "\n".join(system_parts), contents


def to_gemini_tools(tools: Any) -> list | None:
    """Map the loop's tool map to function declarations. None stays None."""
    if tools is None:
        return None
    if isinstance(tools, list):
        return tools
    if isinstance(tools, dict):
        return [
            {"name": str(name), "parameters": {"type": "object", "properties": {}}}
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


__all__ = ["GeminiProvider", "to_gemini_contents", "to_gemini_tools"]
