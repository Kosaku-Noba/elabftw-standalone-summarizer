"""Logging helpers."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from standalone_summarizer.config import AppConfig


def configure_logging(config: AppConfig) -> None:
    log_dir: Path = config.logging.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "standalone-summarizer.log"

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        file_handler = TimedRotatingFileHandler(
            log_file,
            when="midnight",
            backupCount=max(config.logging.retention_days, 1),
            encoding="utf-8",
            utc=True,
        )
        handlers.append(file_handler)
    except OSError:
        logging.getLogger(__name__).warning("Failed to open log file", exc_info=True)

    # logging.basicConfig is a no-op when the root logger already has handlers,
    # so reconfiguration (e.g. different log_dir) would be silently ignored.
    # Reset existing handlers to make this function idempotent.
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
        try:
            existing.close()
        except Exception:  # pragma: no cover - defensive cleanup
            pass

    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=handlers,
    )
