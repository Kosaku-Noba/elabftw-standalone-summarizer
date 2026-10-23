"""Ollama based summarizer backend."""

from __future__ import annotations

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from standalone_summarizer.config import LLMConfig
from standalone_summarizer.summarizer.base import (
    SummarizeRequest,
    SummarizeResponse,
    SummarizerBackend,
)

logger = logging.getLogger(__name__)


class OllamaBackend(SummarizerBackend):
    """Interact with an Ollama HTTP endpoint."""

    def __init__(self, config: LLMConfig) -> None:
        if not config.endpoint_url:
            raise ValueError("LLM_ENDPOINT_URL must be set for the Ollama backend")
        self._config = config
        self._session = requests.Session()
        retry = Retry(
            total=config.retry_attempts,
            backoff_factor=config.retry_backoff_seconds,
            status_forcelist=(408, 429, 500, 502, 503, 504),
            allowed_methods=("POST",),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    @property
    def model_identifier(self) -> str:
        if self._config.model_id:
            return self._config.model_id
        if self._config.model_path:
            return str(self._config.model_path)
        raise ValueError("Model identifier is not configured for Ollama backend")

    def summarize(self, request: SummarizeRequest) -> SummarizeResponse:
        payload: dict[str, Any] = {
            "model": self.model_identifier,
            "prompt": request.prompt,
            "options": {
                "temperature": self._config.temperature,
            },
            "stream": False,
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        if self._config.max_output_tokens:
            payload["options"]["num_predict"] = self._config.max_output_tokens
        url = f"{self._config.endpoint_url}/api/generate"
        logger.debug(
            "Calling Ollama",
            extra={
                "url": url,
                "model": payload["model"],
                "metadata": request.metadata,
            },
        )
        response = self._session.post(url, json=payload, timeout=120)
        response.raise_for_status()
        try:
            data: Any = response.json()
        except ValueError as exc:
            logger.exception("Failed to parse Ollama response", extra={"status_code": response.status_code})
            raise RuntimeError("Invalid JSON response from Ollama") from exc
        summary_text = data.get("response", "")
        return SummarizeResponse(
            summary=summary_text,
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            model=data.get("model", payload["model"]),
        )
