"""llama.cpp based summarizer backend implementation."""

from __future__ import annotations

import logging
from typing import Any

from standalone_summarizer.config import LLMConfig
from standalone_summarizer.summarizer.base import (
    SummarizeRequest,
    SummarizeResponse,
    SummarizerBackend,
)

logger = logging.getLogger(__name__)


class LlamaCppBackend(SummarizerBackend):
    """Wrap llama-cpp-python for local inference."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._llm: Any | None = None
        logger.debug(
            "Initialized LlamaCppBackend",
            extra={
                "model_id": config.model_id,
                "model_path": str(config.model_path) if config.model_path else None,
                "context_window": config.context_window,
            },
        )

    def load(self) -> None:
        if self._llm is not None:
            return
        if not self._config.model_path:
            raise ValueError("LLM model path must be provided for llama.cpp backend")
        try:
            from llama_cpp import Llama  # type: ignore import-not-found
        except ImportError as exc:  # pragma: no cover - runtime guard
            raise RuntimeError(
                "llama-cpp-python is required for the llama.cpp backend. Install it to proceed."
            ) from exc

        logger.info(
            "Loading llama.cpp model",
            extra={
                "model_path": str(self._config.model_path),
                "context_window": self._config.context_window,
            },
        )
        self._llm = Llama(
            model_path=str(self._config.model_path),
            n_ctx=self._config.context_window,
            logits_all=False,
            verbose=False,
        )

    def summarize(self, request: SummarizeRequest) -> SummarizeResponse:
        if self._llm is None:
            raise RuntimeError("Model is not loaded. Call load() before summarize().")

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        kwargs: dict[str, Any] = {
            "messages": messages,
            "temperature": self._config.temperature,
        }
        if self._config.max_output_tokens:
            kwargs["max_tokens"] = self._config.max_output_tokens

        result = self._llm.create_chat_completion(**kwargs)
        choice = result["choices"][0]["message"]["content"].strip()
        usage = result.get("usage", {})
        return SummarizeResponse(
            summary=choice,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            model=result.get("model", self._config.model_id or str(self._config.model_path)),
        )
