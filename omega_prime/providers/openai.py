"""OpenAI wires: Responses by default, chat-completions for compatibles.

Grok subclasses this: xAI speaks chat-completions, so the Grok adapter pins
``api_mode`` there. ``api_mode`` is ``auto`` (Responses on api.openai.com,
chat-completions elsewhere), ``responses``, or ``chat_completions``.
Streaming always follows the chat wire; Responses streaming is deferred.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from omega_prime.providers.base import Provider, ProviderError

OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"


@dataclass
class OpenAIProvider(Provider):
    """POST ``{base_url}/responses`` (or ``/chat/completions``)."""

    name: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    env_vars: tuple = ("OPENAI_API_KEY",)
    api_mode: str = "auto"

    def effective_mode(self) -> str:
        """``responses`` or ``chat_completions`` for this provider."""
        if self.api_mode == "responses":
            return "responses"
        if self.api_mode == "chat_completions":
            return "chat_completions"
        if self.base_url.rstrip("/") == OPENAI_DEFAULT_BASE_URL:
            return "responses"
        return "chat_completions"

    def build_request(
        self, model: str, messages: list, tools: Any, api_key: str
    ) -> tuple[str, dict, dict]:
        if self.effective_mode() == "responses":
            return self._responses_request(model, messages, tools, api_key)
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

    def _responses_request(
        self, model: str, messages: list, tools: Any, api_key: str
    ) -> tuple[str, dict, dict]:
        """POST ``{base_url}/responses``. Stateless: the loop owns history."""
        url = self.base_url.rstrip("/") + "/responses"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": model,
            "input": to_responses_input(messages),
            "store": False,
        }
        wire_tools = to_responses_tools(tools)
        if wire_tools is not None:
            body["tools"] = wire_tools
        return url, headers, body

    def stream_request(
        self, model: str, messages: list, tools: Any, api_key: str
    ) -> tuple[str, dict, dict]:
        """Chat-shape streaming with usage on the final chunk."""
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": model,
            "messages": to_openai_messages(messages),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        wire_tools = to_openai_tools(tools)
        if wire_tools is not None:
            body["tools"] = wire_tools
        return url, headers, body

    def fallback_request(
        self,
        model: str,
        messages: list,
        tools: Any,
        api_key: str,
        error: ProviderError,
    ) -> tuple[str, dict, dict] | None:
        """Chat-completions when Responses is denied. None otherwise."""
        if self.effective_mode() != "responses":
            return None
        text = str(error).lower()
        denied = (
            "404" in text
            or "not found" in text
            or (("401" in text or "403" in text) and "response" in text)
        )
        if not denied:
            return None
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
        if "choices" in payload:
            return _parse_chat_response(self.name, payload)
        if "output" in payload:
            return _parse_responses_response(self.name, payload)
        raise ProviderError(f"{self.name} response has no message: {payload!r}")

    def parse_stream(self, lines: Any) -> tuple[dict[str, Any], dict[str, int] | None]:
        """Accumulate chat-completions SSE deltas into ``(row, usage?)``."""
        texts: list[str] = []
        calls: dict[int, dict[str, Any]] = {}
        usage: dict[str, int] | None = None
        finish: str | None = None
        for event in self._sse_data(lines):
            for choice in event.get("choices") or []:
                if not isinstance(choice, dict):
                    continue
                delta = choice.get("delta") or {}
                if not isinstance(delta, dict):
                    continue
                piece = delta.get("content")
                if isinstance(piece, str) and piece:
                    texts.append(piece)
                for call in delta.get("tool_calls") or []:
                    if not isinstance(call, dict):
                        continue
                    index = call.get("index", 0)
                    if not isinstance(index, int):
                        continue
                    slot = calls.setdefault(
                        index, {"id": "", "name": "", "arguments": ""}
                    )
                    if isinstance(call.get("id"), str):
                        slot["id"] = call["id"]
                    function = call.get("function") or {}
                    if isinstance(function, dict):
                        if isinstance(function.get("name"), str):
                            slot["name"] = function["name"]
                        piece = function.get("arguments")
                        if isinstance(piece, str):
                            slot["arguments"] += piece
                reason = choice.get("finish_reason")
                if isinstance(reason, str) and reason:
                    finish = reason
            block = self._usage_from(
                event,
                "usage",
                (
                    ("prompt_tokens", "prompt_tokens"),
                    ("completion_tokens", "completion_tokens"),
                    ("total_tokens", "total_tokens"),
                ),
            )
            if block is not None:
                usage = block
        row: dict[str, Any] = {"role": "assistant", "content": "".join(texts)}
        merged = [calls[index] for index in sorted(calls) if calls[index]["name"]]
        if merged:
            row["tool_calls"] = [
                {
                    "id": slot["id"],
                    "type": "function",
                    "function": {
                        "name": slot["name"],
                        "arguments": slot["arguments"],
                    },
                }
                for slot in merged
            ]
        if finish:
            row["finish_reason"] = finish
        return row, usage

    def parse_usage(self, payload: dict) -> dict[str, int] | None:
        found = self._usage_from(
            payload,
            "usage",
            (
                ("prompt_tokens", "prompt_tokens"),
                ("completion_tokens", "completion_tokens"),
                ("total_tokens", "total_tokens"),
                ("input_tokens", "prompt_tokens"),
                ("output_tokens", "completion_tokens"),
            ),
        )
        return found


def _parse_chat_response(name: str, payload: dict) -> dict:
    try:
        choices = payload["choices"]
        first = choices[0]
        message = first["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"{name} response has no message: {exc}") from exc
    if not isinstance(message, dict):
        raise ProviderError(f"{name} response message is not an object")
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


def _parse_responses_response(name: str, payload: dict) -> dict:
    """One assistant row from a Responses ``output`` list."""
    if payload.get("status") == "failed":
        error = payload.get("error") or {}
        detail = error.get("message") if isinstance(error, dict) else error
        raise ProviderError(f"{name} response failed: {detail}")
    output = payload.get("output")
    if not isinstance(output, list) or not output:
        raise ProviderError(f"{name} response has no output items")
    texts: list[str] = []
    calls: list[dict] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "message":
            for block in item.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") in ("output_text", "refusal"):
                    texts.append(_text(block.get("text")))
        elif kind == "function_call":
            if not item.get("name"):
                raise ProviderError(f"{name} function_call has no name")
            raw_args = item.get("arguments", {})
            if isinstance(raw_args, dict) or not isinstance(raw_args, str):
                raw_args = json.dumps(raw_args)
            calls.append(
                {
                    "id": str(item.get("call_id", "")),
                    "type": "function",
                    "function": {
                        "name": str(item["name"]),
                        "arguments": raw_args,
                    },
                }
            )
    if not texts and not calls:
        raise ProviderError(f"{name} response has no usable content")
    row: dict[str, Any] = {"role": "assistant", "content": "".join(texts)}
    if calls:
        row["tool_calls"] = calls
    return row


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


def to_responses_input(messages: list) -> list[dict]:
    """Transcript rows as Responses ``input`` items."""
    items: list[dict] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        if role == "tool":
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": str(message.get("tool_call_id", "")),
                    "output": _text(message.get("content")),
                }
            )
            continue
        if role == "assistant":
            for call in message.get("tool_calls") or []:
                if not isinstance(call, dict):
                    continue
                function = call.get("function") or {}
                if not isinstance(function, dict):
                    continue
                items.append(
                    {
                        "type": "function_call",
                        "call_id": str(call.get("id", "")),
                        "name": str(function.get("name", "")),
                        "arguments": _arguments_json(function.get("arguments")),
                    }
                )
        items.append({"role": str(role), "content": _text(message.get("content"))})
    return items


def to_responses_tools(tools: Any) -> list[dict] | None:
    """Tool map as Responses ``function`` tools. None when no tools."""
    if not tools:
        return None
    names = sorted(tools) if isinstance(tools, dict) else []
    if not names:
        return None
    return [
        {
            "type": "function",
            "name": name,
            "parameters": {"type": "object", "properties": {}},
        }
        for name in names
    ]


def _arguments_json(raw: Any) -> str:
    """Tool arguments as a JSON string for the Responses wire."""
    if isinstance(raw, str):
        return raw
    try:
        return json.dumps(raw if raw is not None else {})
    except (TypeError, ValueError):
        return "{}"


__all__ = [
    "OPENAI_DEFAULT_BASE_URL",
    "OpenAIProvider",
    "normalize_tool_call",
    "to_openai_messages",
    "to_openai_tools",
    "to_responses_input",
    "to_responses_tools",
]
