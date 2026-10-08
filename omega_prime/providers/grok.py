"""Grok adapter: xAI's OpenAI-compatible chat completions."""

from __future__ import annotations

from dataclasses import dataclass

from omega_prime.providers.openai import OpenAIProvider

XAI_DEFAULT_BASE_URL = "https://api.x.ai/v1"


@dataclass
class GrokProvider(OpenAIProvider):
    """POST ``{base_url}/chat/completions``. Key from ``XAI_API_KEY``."""

    name: str = "grok"
    base_url: str = XAI_DEFAULT_BASE_URL
    env_vars: tuple = ("XAI_API_KEY",)
    api_mode: str = "chat_completions"


__all__ = ["XAI_DEFAULT_BASE_URL", "GrokProvider"]
