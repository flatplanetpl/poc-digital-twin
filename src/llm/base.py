"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Iterator

from llama_index.core.llms import LLM


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display."""
        pass

    @property
    @abstractmethod
    def is_local(self) -> bool:
        """Whether this provider runs locally (offline)."""
        pass

    @abstractmethod
    def get_llama_index_llm(self) -> LLM:
        """Get LlamaIndex-compatible LLM instance.

        Returns:
            LlamaIndex LLM object for use with query engines
        """
        pass

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Generate completion for a prompt.

        Args:
            prompt: Input prompt text

        Returns:
            Generated completion text
        """
        pass

    @abstractmethod
    def stream(self, prompt: str) -> Iterator[str]:
        """Stream completion tokens for a prompt.

        Args:
            prompt: Input prompt text

        Yields:
            Generated tokens one at a time
        """
        pass

    def is_available(self) -> bool:
        """Check if provider is available and configured.

        Returns:
            True if provider can be used
        """
        return True
