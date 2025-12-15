"""Factory for creating LLM providers."""

from typing import Literal

from src.config import settings

from .anthropic_provider import AnthropicProvider
from .base import BaseLLM
from .gpt4all_provider import GPT4AllProvider
from .openai_provider import OpenAIProvider

ProviderType = Literal["gpt4all", "openai", "anthropic"]

_PROVIDERS: dict[str, type[BaseLLM]] = {
    "gpt4all": GPT4AllProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def create_llm(provider: ProviderType | None = None) -> BaseLLM:
    """Create an LLM provider instance.

    Args:
        provider: Provider type to create. If None, uses settings default.

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If provider type is unknown
    """
    provider = provider or settings.llm_provider

    if provider not in _PROVIDERS:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(f"Unknown provider '{provider}'. Available: {available}")

    return _PROVIDERS[provider]()


def get_available_providers() -> list[dict]:
    """Get list of available LLM providers with their status.

    Returns:
        List of dicts with provider info and availability
    """
    providers = []

    for name, provider_class in _PROVIDERS.items():
        try:
            instance = provider_class()
            providers.append({
                "id": name,
                "name": instance.name,
                "is_local": instance.is_local,
                "available": instance.is_available(),
            })
        except Exception as e:
            providers.append({
                "id": name,
                "name": name,
                "is_local": name == "gpt4all",
                "available": False,
                "error": str(e),
            })

    return providers
