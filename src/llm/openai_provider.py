"""OpenAI LLM provider."""

from typing import Iterator

from llama_index.core.llms import LLM
from llama_index.llms.openai import OpenAI

from src.config import settings

from .base import BaseLLM


class OpenAIProvider(BaseLLM):
    """OpenAI API LLM provider."""

    def __init__(self):
        self._client = None
        self._llama_index_llm: OpenAI | None = None

    @property
    def name(self) -> str:
        return f"OpenAI ({settings.openai_model})"

    @property
    def is_local(self) -> bool:
        return False

    def get_llama_index_llm(self) -> LLM:
        if self._llama_index_llm is None:
            self._llama_index_llm = OpenAI(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
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
        return bool(settings.openai_api_key)
