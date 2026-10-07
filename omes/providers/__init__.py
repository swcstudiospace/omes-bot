"""Model providers behind an injected transport. No socket in tests."""

from __future__ import annotations

from omes.providers.anthropic import AnthropicProvider
from omes.providers.base import Provider, ProviderError, ProviderModel, Transport
from omes.providers.fake import FakeTransport
from omes.providers.gemini import GeminiProvider
from omes.providers.grok import GrokProvider
from omes.providers.http import HttpTransport
from omes.providers.ollama import OllamaProvider
from omes.providers.openai import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "FakeTransport",
    "GeminiProvider",
    "GrokProvider",
    "HttpTransport",
    "OllamaProvider",
    "OpenAIProvider",
    "Provider",
    "ProviderError",
    "ProviderModel",
    "Transport",
]
