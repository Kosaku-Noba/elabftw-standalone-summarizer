"""Configuration primitives for the standalone summarizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class ElabConfig:
    """Connection settings for the eLabFTW REST API."""

    base_url: str
    api_key: str
    verify_ssl: bool = True
    timeout_seconds: float = 30.0
    page_size: int = 50
    max_pages: int = 20
    retry_attempts: int = 3
    retry_backoff_seconds: float = 2.0


@dataclass(frozen=True)
class LLMConfig:
    """Runtime and model configuration for the local LLM backend."""

    backend: str
    model_id: str | None = None
    model_path: Path | None = None
    endpoint_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.2
    max_input_chars: int = 3000
    system_prompt_path: Path | None = None
    context_window: int = 4096
    max_output_tokens: int | None = None
    retry_attempts: int = 3
    retry_backoff_seconds: float = 2.0


@dataclass(frozen=True)
class SchedulerConfig:
    """Polling cadence and batch sizes."""

    interval_seconds: int = 300
    max_items_per_cycle: int = 10


@dataclass(frozen=True)
class LoggingConfig:
    """Logging and audit trail destinations."""

    level: str = "INFO"
    log_dir: Path = Path("/var/log/elabbot")
    retention_days: int = 30


@dataclass(frozen=True)
class AppConfig:
    """Aggregate configuration."""

    elab: ElabConfig
    llm: LLMConfig
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    tags: List[str] = field(default_factory=lambda: ["summarize"])
    teams_tag_map: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> "AppConfig":
        """Load configuration from provided environment mapping."""

        env = env or os.environ

        elab_config = ElabConfig(
            base_url=env.get("ELAB_BASE_URL", "https://elab.local/api/v2"),
            api_key=env.get("ELAB_API_KEY", ""),
            verify_ssl=env.get("ELAB_VERIFY_SSL", "true").lower() == "true",
            timeout_seconds=float(env.get("ELAB_TIMEOUT", "30")),
            page_size=int(env.get("ELAB_PAGE_SIZE", "50")),
            max_pages=int(env.get("ELAB_MAX_PAGES", "20")),
            retry_attempts=int(env.get("ELAB_RETRY_ATTEMPTS", "3")),
            retry_backoff_seconds=float(env.get("ELAB_RETRY_BACKOFF_SECONDS", "2.0")),
        )

        llm_config = LLMConfig(
            backend=env.get("LLM_BACKEND", "ollama"),
            model_id=env.get("LLM_MODEL_ID") or env.get("LLM_MODEL"),
            model_path=_optional_path(env.get("LLM_MODEL_PATH")),
            endpoint_url=env.get("LLM_ENDPOINT_URL"),
            api_key=env.get("LLM_API_KEY"),
            temperature=float(env.get("LLM_TEMPERATURE", "0.2")),
            max_input_chars=int(env.get("LLM_MAX_INPUT_CHARS", "3000")),
            system_prompt_path=_optional_path(env.get("LLM_SYSTEM_PROMPT")),
            context_window=int(env.get("LLM_CONTEXT_WINDOW", "4096")),
            max_output_tokens=_optional_int(env.get("LLM_MAX_OUTPUT_TOKENS")),
            retry_attempts=int(env.get("LLM_RETRY_ATTEMPTS", "3")),
            retry_backoff_seconds=float(env.get("LLM_RETRY_BACKOFF_SECONDS", "2.0")),
        )

        scheduler_config = SchedulerConfig(
            interval_seconds=int(env.get("SCHEDULER_INTERVAL_SECONDS", "300")),
            max_items_per_cycle=int(env.get("SCHEDULER_MAX_ITEMS", "10")),
        )

        logging_config = LoggingConfig(
            level=env.get("LOG_LEVEL", "INFO"),
            log_dir=_optional_path(env.get("LOG_DIR")) or Path("/var/log/elabbot"),
            retention_days=int(env.get("LOG_RETENTION_DAYS", "30")),
        )

        tags = [tag.strip() for tag in env.get("TARGET_TAGS", "summarize").split(",") if tag.strip()]

        # TEAMS_TAG_MAP format: "tag1=https://webhook1,tag2=https://webhook2"
        # or a single default: TEAMS_WEBHOOK_URL (applies to all)
        teams_tag_map: Dict[str, str] = {}
        raw_map = env.get("TEAMS_TAG_MAP", "")
        if raw_map:
            for pair in raw_map.split(","):
                if "=" in pair:
                    k, _, v = pair.partition("=")
                    teams_tag_map[k.strip()] = v.strip()
        elif env.get("TEAMS_WEBHOOK_URL"):
            for t in tags:
                teams_tag_map[t] = env["TEAMS_WEBHOOK_URL"]

        return AppConfig(
            elab=elab_config,
            llm=llm_config,
            scheduler=scheduler_config,
            logging=logging_config,
            tags=tags,
            teams_tag_map=teams_tag_map,
        )


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()



def _optional_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
