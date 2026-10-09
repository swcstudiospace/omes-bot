# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""In-process Prime pa-ai completions in the existing Omega conversation loop.

The model is a complete, camelCase Prime catalog descriptor, not an Omega
provider name. Native loading and credential resolution happen only on a call.
``prime_message`` retains the lossless assistant wire for durable replay,
including opaque thinking/text/tool signatures and provider response metadata.
"""

from __future__ import annotations

import copy
import json
import time
from typing import Any

from omega_prime.prime_kernel.native import load_extension
from omega_prime.providers.base import Provider, ProviderError
from omega_prime.providers.openai import normalize_tool_call, to_openai_tools

# Matches the pinned pa-ai env_api_keys.rs. The broker owns environment reads.
_ENV_VARS = {
    "github-copilot": ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"),
    "anthropic": ("ANTHROPIC_OAUTH_TOKEN", "ANTHROPIC_API_KEY"),
    "openai": ("OPENAI_API_KEY",),
    "azure-openai-responses": ("AZURE_OPENAI_API_KEY",),
    "prime-inference": ("PRIME_API_KEY",),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "google": ("GEMINI_API_KEY",),
    "google-vertex": ("GOOGLE_CLOUD_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "cerebras": ("CEREBRAS_API_KEY",),
    "xai": ("XAI_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "vercel-ai-gateway": ("AI_GATEWAY_API_KEY",),
    "zai": ("ZAI_API_KEY",),
    "mistral": ("MISTRAL_API_KEY",),
    "minimax": ("MINIMAX_API_KEY",),
    "minimax-cn": ("MINIMAX_CN_API_KEY",),
    "moonshotai": ("MOONSHOT_API_KEY",),
    "moonshotai-cn": ("MOONSHOT_API_KEY",),
    "huggingface": ("HF_TOKEN",),
    "fireworks": ("FIREWORKS_API_KEY",),
    "opencode": ("OPENCODE_API_KEY",),
    "opencode-go": ("OPENCODE_API_KEY",),
    "kimi-coding": ("KIMI_API_KEY",),
    "cloudflare-workers-ai": ("CLOUDFLARE_API_KEY",),
    "cloudflare-ai-gateway": ("CLOUDFLARE_API_KEY",),
    "xiaomi": ("XIAOMI_API_KEY",),
    "xiaomi-token-plan-cn": ("XIAOMI_TOKEN_PLAN_CN_API_KEY",),
    "xiaomi-token-plan-ams": ("XIAOMI_TOKEN_PLAN_AMS_API_KEY",),
    "xiaomi-token-plan-sgp": ("XIAOMI_TOKEN_PLAN_SGP_API_KEY",),
}


class PrimeProviderModel:
    """A ``Model.complete`` adapter backed exclusively by native ``ai.complete``.

    Credentials follow ``ProviderModel``: an explicit key (or options.apiKey)
    without a broker, otherwise a fresh broker approval for the descriptor's
    baseUrl. There is no implicit Python provider or ambient-key fallback.
    Tools must carry real schemas: an OpenAI/Prime definition list or an object
    exposing ``schemas()`` (including a dispatch map with registry schemas).
    """

    def __init__(
        self,
        model: dict,
        api_key: str | None = None,
        broker: Any = None,
        options: dict | None = None,
    ) -> None:
        if not isinstance(model, dict):
            raise ProviderError("Prime needs a full model descriptor")
        for field in ("id", "provider", "api", "baseUrl"):
            if not isinstance(model.get(field), str) or not model[field]:
                raise ProviderError(f"Prime model descriptor needs {field}")
        if options is not None and not isinstance(options, dict):
            raise ProviderError("Prime options must be an object")
        self.model = copy.deepcopy(model)
        self.api_key = api_key
        self.broker = broker
        self.options = copy.deepcopy(options or {})
        self.provider = Provider(
            name=model["provider"],
            base_url=model["baseUrl"],
            env_vars=_ENV_VARS.get(model["provider"], ()),
            api_mode=model["api"],
        )
        self.last_usage: dict[str, int] | None = None
        self.last_fallback = False

    def complete(self, messages: list, tools: Any = None) -> dict:
        """Translate, approve credentials, call pa-ai, and return an Omega row."""
        self.last_usage = None
        key = self.api_key if self.api_key is not None else self.options.get("apiKey")
        if self.broker is not None:
            key = self.broker.key_for(self.provider, self.model["baseUrl"])
        if not isinstance(key, str) or not key:
            raise ProviderError(f"{self.provider.name} needs an API key")
        try:
            context = _context(messages, tools, self.model)
        except ProviderError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(
                "Prime transcript or tools contain malformed content"
            ) from exc
        options = {**self.options, "apiKey": key}
        try:
            ai = load_extension().ai
            if not callable(getattr(ai, "complete", None)):
                raise AttributeError("native ai.complete is unavailable")
        except (ImportError, AttributeError, OSError) as exc:
            raise ProviderError(
                "Prime native ai.complete is unavailable; build the extension"
            ) from exc
        try:
            payload = ai.complete(self.model, context, options)
            row = _assistant_row(payload)
        except ProviderError as exc:
            raise ProviderError(self._redact(str(exc), key)) from None
        except Exception as exc:
            raise ProviderError(
                self._redact(f"Prime completion failed: {exc}", key)
            ) from None
        self.last_usage = _usage(payload)
        return row

    def _redact(self, text: str, key: str) -> str:
        text = text.replace(key, "[REDACTED]")
        if self.broker is not None:
            text = self.broker.redact(text)
        return text


def _context(messages: list, tools: Any, model: dict) -> dict:
    system: list[str] = []
    wire: list[dict] = []
    call_names: dict[str, str] = {}
    for row in messages:
        if not isinstance(row, dict):
            raise ProviderError("Prime transcript rows must be objects")
        role = row.get("role", "user")
        timestamp = row.get("timestamp", int(time.time() * 1000))
        if role == "system":
            blocks = _blocks(row.get("content"))
            if any(block["type"] != "text" for block in blocks):
                raise ProviderError("Prime system content must be text")
            system.append("\n".join(block["text"] for block in blocks))
        elif role == "user":
            content = row.get("content")
            wire.append(
                {
                    "role": "user",
                    "content": content
                    if isinstance(content, str)
                    else _blocks(content),
                    "timestamp": timestamp,
                }
            )
        elif role == "assistant":
            raw = row.get("prime_message")
            if raw is not None:
                projected = _assistant_row(raw)
                if projected["content"] != _assistant_text(
                    row.get("content")
                ) or _calls(projected) != _calls(row):
                    raise ProviderError(
                        "Prime assistant metadata does not match its content/tool calls"
                    )
                assistant = copy.deepcopy(raw)
            else:
                assistant = _historical_assistant(row, model, timestamp)
            wire.append(assistant)
            for block in assistant["content"]:
                if block["type"] == "toolCall":
                    call_names[block["id"]] = block["name"]
        elif role == "tool":
            call_id = row.get("tool_call_id")
            if not isinstance(call_id, str) or not call_id:
                raise ProviderError("Prime tool result needs a tool_call_id")
            content = row.get("content")
            result: dict[str, Any] = {
                "role": "toolResult",
                "toolCallId": call_id,
                "toolName": row.get("name") or call_names.get(call_id, ""),
                "content": _blocks(content),
                "isError": bool(
                    row.get("is_error", row.get("isError", _tool_error(content)))
                ),
                "timestamp": timestamp,
            }
            if "details" in row:
                result["details"] = copy.deepcopy(row["details"])
            wire.append(result)
        else:
            raise ProviderError(f"Prime does not support transcript role {role!r}")
    context: dict[str, Any] = {"messages": wire}
    if system:
        context["systemPrompt"] = "\n".join(system)
    if tools is not None:
        context["tools"] = _tools(tools)
    return context


def _tools(tools: Any) -> list[dict]:
    schemas = getattr(tools, "schemas", None)
    if callable(schemas):
        tools = schemas()
    if isinstance(tools, dict):
        if not tools:
            return []
        raise ProviderError(
            "Prime tools need registered schemas, not a plain callable map"
        )
    wire = to_openai_tools(tools)
    if not isinstance(wire, list):
        raise ProviderError("Prime tools must be a definition list or expose schemas()")
    result: list[dict] = []
    for item in wire:
        if not isinstance(item, dict):
            raise ProviderError("Prime tool definition must be an object")
        function = item.get("function", item)
        if (
            not isinstance(function, dict)
            or not isinstance(function.get("name"), str)
            or not function["name"]
        ):
            raise ProviderError("Prime tool definition needs a name")
        if not isinstance(function.get("parameters"), dict):
            raise ProviderError(
                "Prime tool definition needs its registered parameters schema"
            )
        description = function.get("description", "")
        if not isinstance(description, str):
            raise ProviderError("Prime tool description must be text")
        result.append(
            {
                "name": function["name"],
                "description": description,
                "parameters": copy.deepcopy(function["parameters"]),
            }
        )
    return result


def _arguments(raw: Any) -> dict:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError as exc:
            raise ProviderError("Prime tool arguments must be valid JSON") from exc
    if not isinstance(raw, dict):
        raise ProviderError("Prime tool arguments must be a JSON object")
    return copy.deepcopy(raw)


def _calls(row: dict) -> list[dict]:
    result = []
    for call in row.get("tool_calls") or []:
        normalized = normalize_tool_call(call)
        normalized["function"]["arguments"] = _arguments(
            normalized["function"]["arguments"]
        )
        result.append(normalized)
    return result


def _historical_assistant(row: dict, model: dict, timestamp: int) -> dict:
    content = row.get("content")
    blocks = _blocks(content, assistant=True)
    thinking = row.get("thinking", row.get("reasoning_content"))
    if isinstance(thinking, str) and thinking:
        block = {"type": "thinking", "thinking": thinking}
        signature = row.get("thinkingSignature", row.get("thinking_signature"))
        if signature is not None:
            block["thinkingSignature"] = signature
        blocks.insert(0, block)
    for call in _calls(row):
        blocks.append(
            {
                "type": "toolCall",
                "id": call["id"],
                "name": call["function"]["name"],
                "arguments": call["function"]["arguments"],
            }
        )
    return {
        "role": "assistant",
        "content": blocks,
        "api": row.get("api", model["api"]),
        "provider": row.get("provider", model["provider"]),
        "model": row.get("model", model["id"]),
        "usage": row.get("usage", _zero_usage()),
        "stopReason": (
            "toolUse"
            if any(block["type"] == "toolCall" for block in blocks)
            else "stop"
        ),
        "timestamp": timestamp,
    }


def _blocks(content: Any, *, assistant: bool = False) -> list[dict]:
    if content is None:
        return []
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if not isinstance(content, list):
        return [{"type": "text", "text": str(content)}]
    result: list[dict] = []
    for block in content:
        if not isinstance(block, dict):
            raise ProviderError("Prime content blocks must be objects")
        kind = block.get("type")
        if kind in ("text", "input_text", "output_text"):
            result.append({**copy.deepcopy(block), "type": "text"})
        elif assistant and kind in ("thinking", "toolCall"):
            result.append(copy.deepcopy(block))
        elif assistant:
            raise ProviderError(f"Prime assistant content does not support {kind!r}")
        elif kind == "image" and "data" in block and "mimeType" in block:
            result.append(copy.deepcopy(block))
        elif kind == "image" and isinstance(block.get("source"), dict):
            source = block["source"]
            if source.get("type") != "base64":
                raise ProviderError("Prime images require embedded base64 data")
            result.append(
                {
                    "type": "image",
                    "data": source["data"],
                    "mimeType": source["media_type"],
                }
            )
        elif kind in ("image_url", "input_image"):
            image = block.get("image_url")
            url = image.get("url") if isinstance(image, dict) else image
            if (
                not isinstance(url, str)
                or not url.startswith("data:")
                or ";base64," not in url
            ):
                raise ProviderError(
                    "Prime images require a base64 data URL; remote URLs are not fetched"
                )
            header, data = url[5:].split(";base64,", 1)
            result.append({"type": "image", "data": data, "mimeType": header})
        elif "inlineData" in block or "inline_data" in block:
            image = block.get("inlineData", block.get("inline_data"))
            if not isinstance(image, dict):
                raise ProviderError("Prime inline image must be an object")
            result.append(
                {
                    "type": "image",
                    "data": image["data"],
                    "mimeType": image.get("mimeType", image.get("mime_type")),
                }
            )
        else:
            raise ProviderError(f"Prime content does not support {kind!r}")
    return result


def _assistant_text(content: Any) -> str:
    return "".join(
        block["text"]
        for block in _blocks(content, assistant=True)
        if block["type"] == "text"
    )


def _assistant_row(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("role") != "assistant":
        raise ProviderError("Prime returned no assistant message")
    stop = payload.get("stopReason")
    if stop in ("error", "aborted"):
        message = payload.get("errorMessage") or "provider completion failed"
        raise ProviderError(f"Prime {stop}: {message}")
    if stop not in ("stop", "length", "toolUse", "tool_calls"):
        raise ProviderError("Prime returned an unknown stopReason")
    content = payload.get("content")
    if not isinstance(content, list):
        raise ProviderError("Prime returned no assistant content blocks")
    texts: list[str] = []
    thoughts: list[str] = []
    calls: list[dict] = []
    for block in content:
        if not isinstance(block, dict):
            raise ProviderError("Prime returned a malformed assistant block")
        kind = block.get("type")
        if kind == "text" and isinstance(block.get("text"), str):
            texts.append(block["text"])
        elif kind == "thinking" and isinstance(block.get("thinking"), str):
            thoughts.append(block["thinking"])
        elif (
            kind == "toolCall"
            and isinstance(block.get("name"), str)
            and block["name"]
            and isinstance(block.get("id"), str)
        ):
            calls.append(
                {
                    "id": block["id"],
                    "type": "function",
                    "function": {
                        "name": block["name"],
                        "arguments": json.dumps(
                            _arguments(block.get("arguments")), ensure_ascii=False
                        ),
                    },
                }
            )
        else:
            raise ProviderError("Prime returned an unusable assistant content block")
    row: dict[str, Any] = {
        "role": "assistant",
        "content": "".join(texts),
        "finish_reason": "tool_calls" if stop in ("toolUse", "tool_calls") else stop,
        "prime_message": copy.deepcopy(payload),
    }
    if thoughts:
        row["thinking"] = "".join(thoughts)
    if calls:
        row["tool_calls"] = calls
    return row


def _tool_error(content: Any) -> bool:
    if isinstance(content, str):
        if content.startswith("error:"):
            return True
        try:
            content = json.loads(content)
        except ValueError:
            return False
    return isinstance(content, dict) and bool(content.get("error"))


def _zero_usage() -> dict:
    return {
        "input": 0,
        "output": 0,
        "cacheRead": 0,
        "cacheWrite": 0,
        "totalTokens": 0,
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
    }


def _usage(payload: dict) -> dict[str, int] | None:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    found: dict[str, int] = {}
    for wire, normalized in (
        ("input", "prompt_tokens"),
        ("output", "completion_tokens"),
        ("totalTokens", "total_tokens"),
        ("cacheRead", "cache_read_tokens"),
        ("cacheWrite", "cache_write_tokens"),
    ):
        value = usage.get(wire)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            found[normalized] = value
    if "prompt_tokens" in found:
        found["prompt_tokens"] += found.get("cache_read_tokens", 0) + found.get(
            "cache_write_tokens", 0
        )
    return found or None


__all__ = ["PrimeProviderModel"]
