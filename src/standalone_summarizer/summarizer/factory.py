"""Factory helpers to initialize summarizer backends."""

from __future__ import annotations

from standalone_summarizer.config import LLMConfig
from standalone_summarizer.summarizer.base import SummarizerBackend
from standalone_summarizer.summarizer.backends import LlamaCppBackend, OllamaBackend, MockBackend, AzureOpenAIBackend


def create_backend(config: LLMConfig) -> SummarizerBackend:
    backend = config.backend.lower()
    if backend == "ollama":
        return OllamaBackend(config)
    if backend in {"llamacpp", "llama.cpp"}:
        instance = LlamaCppBackend(config)
        return instance
    if backend in {"azure", "azure_openai", "azureopenai"}:
        return AzureOpenAIBackend(config)
    if backend == "mock":
        return MockBackend(config)
    raise ValueError(f"Unsupported LLM backend: {config.backend}")
