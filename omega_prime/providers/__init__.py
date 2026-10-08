"""Model providers behind an injected transport. No socket in tests."""

from __future__ import annotations

from omega_prime.providers.anthropic import AnthropicProvider
from omega_prime.providers.base import Provider, ProviderError, ProviderModel, Transport
from omega_prime.providers.fake import FakeTransport
from omega_prime.providers.gemini import GeminiProvider
from omega_prime.providers.grok import GrokProvider
from omega_prime.providers.http import HttpTransport
from omega_prime.providers.ollama import OllamaProvider
from omega_prime.providers.openai import OpenAIProvider

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
