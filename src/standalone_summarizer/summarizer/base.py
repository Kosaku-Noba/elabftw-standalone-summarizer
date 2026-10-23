"""Interfaces for summarization backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class SummarizeRequest:
    """A single inference request to a language model."""

    prompt: str
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class SummarizeResponse:
    summary: str
    tokens_in: int
    tokens_out: int
    model: str


class SummarizerBackend:
    """Uniform interface across different LLM runtimes."""

    def summarize(self, request: SummarizeRequest) -> SummarizeResponse:  # pragma: no cover - abstract
        raise NotImplementedError

    def load(self) -> None:  # pragma: no cover - optional hook
        """Load model weights if the backend requires explicit initialisation."""
        return None
