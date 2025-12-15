"""Anthropic Claude LLM provider."""

from typing import Iterator

from llama_index.core.llms import LLM
from llama_index.llms.anthropic import Anthropic

from src.config import settings

from .base import BaseLLM


class AnthropicProvider(BaseLLM):
    """Anthropic Claude API LLM provider."""

    def __init__(self):
        self._llama_index_llm: Anthropic | None = None

    @property
    def name(self) -> str:
        return f"Claude ({settings.anthropic_model})"

    @property
    def is_local(self) -> bool:
        return False

    def get_llama_index_llm(self) -> LLM:
        if self._llama_index_llm is None:
            self._llama_index_llm = Anthropic(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
            )
        return self._llama_index_llm

    def complete(self, prompt: str) -> str:
        llm = self.get_llama_index_llm()
        response = llm.complete(prompt)
        return response.text

    def stream(self, prompt: str) -> Iterator[str]:
        llm = self.get_llama_index_llm()
        for chunk in llm.stream_complete(prompt):
            if chunk.delta:
                yield chunk.delta

    def is_available(self) -> bool:
        return bool(settings.anthropic_api_key)
