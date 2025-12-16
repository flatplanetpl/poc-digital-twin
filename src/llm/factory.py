"""Factory for creating LLM providers.

FR-P0-2: Offline / No-Leak Mode
- Enforces offline mode restrictions
- Prevents accidental use of cloud LLMs when offline
"""

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

# Cloud providers that require internet
_CLOUD_PROVIDERS = {"openai", "anthropic"}


class OfflineModeError(Exception):
    """Raised when trying to use cloud LLM in offline mode."""

    pass


def create_llm(provider: ProviderType | None = None) -> BaseLLM:
    """Create an LLM provider instance.

    FR-P0-2: Enforces offline mode restrictions. In offline mode,
    only gpt4all (local) provider is allowed.

    Args:
        provider: Provider type to create. If None, uses settings default.

    Returns:
        Configured LLM provider instance

    Raises:
        ValueError: If provider type is unknown
        OfflineModeError: If trying to use cloud LLM in offline mode
    """
    provider = provider or settings.llm_provider

    if provider not in _PROVIDERS:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(f"Unknown provider '{provider}'. Available: {available}")

    # FR-P0-2: Enforce offline mode
    if settings.offline_mode and provider in _CLOUD_PROVIDERS:
        raise OfflineModeError(
            f"Cannot use '{provider}' in offline mode. "
            f"Only 'gpt4all' is available. "
            f"Set OFFLINE_MODE=false in .env to enable cloud providers."
        )

    # FR-P0-2: Enforce allow_cloud_llm setting
    if not settings.allow_cloud_llm and provider in _CLOUD_PROVIDERS:
        raise OfflineModeError(
            f"Cloud LLM '{provider}' is disabled by configuration. "
            f"Set ALLOW_CLOUD_LLM=true in .env to enable cloud providers."
        )

    return _PROVIDERS[provider]()


def get_available_providers() -> list[dict]:
    """Get list of available LLM providers with their status.

    FR-P0-2: Respects offline mode - cloud providers marked unavailable.

    Returns:
        List of dicts with provider info and availability
    """
    providers = []
    allowed_providers = settings.available_llm_providers

    for name, provider_class in _PROVIDERS.items():
        # Check if provider is allowed in current mode
        is_allowed = name in allowed_providers

        try:
            instance = provider_class()
            is_available = instance.is_available() and is_allowed

            provider_info = {
                "id": name,
                "name": instance.name,
                "is_local": instance.is_local,
                "available": is_available,
            }

            # Add reason if not available due to offline mode
            if not is_allowed:
                provider_info["disabled_reason"] = (
                    "offline_mode" if settings.offline_mode else "cloud_disabled"
                )

            providers.append(provider_info)

        except Exception as e:
            providers.append({
                "id": name,
                "name": name,
                "is_local": name == "gpt4all",
                "available": False,
                "error": str(e),
            })

    return providers


def is_offline_mode() -> bool:
    """Check if system is in offline mode.

    Returns:
        True if offline mode is active
    """
    return settings.is_offline
