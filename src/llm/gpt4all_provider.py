"""GPT4All local LLM provider."""

from typing import Iterator

from gpt4all import GPT4All
from llama_index.core.llms import CustomLLM, CompletionResponse, LLMMetadata
from llama_index.core.llms.callbacks import llm_completion_callback

from src.config import settings

from .base import BaseLLM


class GPT4AllLlamaIndex(CustomLLM):
    """LlamaIndex wrapper for GPT4All."""

    model_name: str = settings.gpt4all_model
    _model: GPT4All | None = None

    @property
    def model(self) -> GPT4All:
        if self._model is None:
            self._model = GPT4All(self.model_name)
        return self._model

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            model_name=self.model_name,
            is_chat_model=True,
        )

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs) -> CompletionResponse:
        response = self.model.generate(prompt)
        return CompletionResponse(text=response)

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs) -> Iterator[CompletionResponse]:
        response_text = ""
        for token in self.model.generate(prompt, streaming=True):
            response_text += token
            yield CompletionResponse(text=response_text, delta=token)


class GPT4AllProvider(BaseLLM):
    """GPT4All local LLM provider."""

    def __init__(self):
        self._model: GPT4All | None = None
        self._llama_index_llm: GPT4AllLlamaIndex | None = None

    @property
    def name(self) -> str:
        return f"GPT4All ({settings.gpt4all_model})"

    @property
    def is_local(self) -> bool:
        return True

    @property
    def model(self) -> GPT4All:
        if self._model is None:
            self._model = GPT4All(settings.gpt4all_model)
        return self._model

    def get_llama_index_llm(self):
        if self._llama_index_llm is None:
            self._llama_index_llm = GPT4AllLlamaIndex()
        return self._llama_index_llm

    def complete(self, prompt: str) -> str:
        return self.model.generate(prompt)

    def stream(self, prompt: str) -> Iterator[str]:
        for token in self.model.generate(prompt, streaming=True):
            yield token

    def is_available(self) -> bool:
        try:
            # Check if model file exists or can be downloaded
            GPT4All(settings.gpt4all_model)
            return True
        except Exception:
            return False
