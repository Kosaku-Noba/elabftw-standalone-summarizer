"""Azure OpenAI based summarizer backend.

Supports both the Chat Completions API and the newer Responses API.
The API style is auto-detected from the endpoint URL:
  - URL containing ``/openai/responses`` → Responses API
  - Everything else → Chat Completions API (default)
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

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

DEFAULT_API_VERSION = "2024-02-15-preview"


def parse_azure_endpoint(
    raw_url: str, deployment: str | None
) -> tuple[str, str, str, str]:
    """Return ``(base_url, deployment, api_version, api_style)``.

    *api_style* is ``"responses"`` when the URL contains ``/openai/responses``,
    otherwise ``"chat"``.
    """
    parsed = urlparse(raw_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    api_style = "responses" if "/openai/responses" in parsed.path else "chat"

    m = re.search(r"/openai/deployments/([^/]+)", parsed.path)
    if m:
        deployment = m.group(1)

    api_version = DEFAULT_API_VERSION
    if parsed.query:
        for part in parsed.query.split("&"):
            if part.startswith("api-version="):
                api_version = part.split("=", 1)[1]

    return base, deployment or "", api_version, api_style


class AzureOpenAIBackend(SummarizerBackend):
    """Interact with Azure OpenAI API."""

    def __init__(self, config: LLMConfig) -> None:
        if not config.endpoint_url:
            raise ValueError("LLM_ENDPOINT_URL must be set for Azure OpenAI backend")
        if not config.api_key:
            raise ValueError("LLM_API_KEY must be set for Azure OpenAI backend")

        self._base, self._deployment, self._api_version, self._api_style = (
            parse_azure_endpoint(config.endpoint_url, config.model_id)
        )

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
        self._session.headers.update({"api-key": config.api_key})

    @property
    def model_identifier(self) -> str:
        return self._deployment or self._config.model_id or "unknown"

    # ── Responses API ────────────────────────────────────────────────────
    def _call_responses(self, request: SummarizeRequest) -> SummarizeResponse:
        url = f"{self._base}/openai/responses?api-version={self._api_version}"

        instructions = request.system_prompt or None
        payload: dict[str, Any] = {
            "model": self._deployment or self._config.model_id,
            "input": request.prompt,
        }
        if instructions:
            payload["instructions"] = instructions
        if self._config.max_output_tokens:
            payload["max_output_tokens"] = self._config.max_output_tokens
        if self._config.temperature:
            payload["temperature"] = self._config.temperature

        logger.debug("Calling Azure OpenAI Responses API", extra={"url": url})
        response = self._session.post(url, json=payload, timeout=120)
        response.raise_for_status()
        data: Any = response.json()

        if "error" in data:
            raise RuntimeError(f"Azure OpenAI error: {data['error']}")

        # Extract text from output items
        summary_parts: list[str] = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        summary_parts.append(content.get("text", ""))

        usage = data.get("usage", {})
        return SummarizeResponse(
            summary="".join(summary_parts),
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            model=data.get("model", self.model_identifier),
        )

    # ── Chat Completions API ─────────────────────────────────────────────
    def _call_chat(self, request: SummarizeRequest) -> SummarizeResponse:
        if not self._deployment:
            raise ValueError("Deployment name is required for Chat Completions API. Set LLM_MODEL_ID.")

        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": self._config.temperature,
        }
        if self._config.max_output_tokens:
            payload["max_tokens"] = self._config.max_output_tokens

        url = (
            f"{self._base}/openai/deployments/{self._deployment}"
            f"/chat/completions?api-version={self._api_version}"
        )

        logger.debug("Calling Azure OpenAI Chat Completions API", extra={"url": url})
        response = self._session.post(url, json=payload, timeout=120)
        response.raise_for_status()
        data: Any = response.json()

        if "error" in data:
            raise RuntimeError(f"Azure OpenAI error: {data['error']}")

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("No choices returned from Azure OpenAI")

        usage = data.get("usage", {})
        return SummarizeResponse(
            summary=choices[0].get("message", {}).get("content", ""),
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            model=data.get("model", self.model_identifier),
        )

    # ── Public interface ─────────────────────────────────────────────────
    def summarize(self, request: SummarizeRequest) -> SummarizeResponse:
        if self._api_style == "responses":
            return self._call_responses(request)
        return self._call_chat(request)
