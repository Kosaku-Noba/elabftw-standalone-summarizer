"""FastAPI service exposing health and metrics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI

from standalone_summarizer.config import AppConfig
from standalone_summarizer.logging_utils import configure_logging
from standalone_summarizer.state import StateStore


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or AppConfig.from_env()
    configure_logging(config)

    app = FastAPI(title="Standalone Summarizer", version="0.1.0")
    start_time = datetime.now(timezone.utc)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {
            "status": "ok",
            "tags": config.tags,
            "scheduler_interval_seconds": config.scheduler.interval_seconds,
        }

    @app.get("/metrics")
    async def metrics() -> dict[str, Any]:
        store = StateStore()
        processed = sum(1 for _ in store.iter_all())
        uptime = (datetime.now(timezone.utc) - start_time).total_seconds()
        return {
            "processed_count": processed,
            "uptime_seconds": uptime,
            "log_directory": str(config.logging.log_dir),
        }

    return app


app = create_app()
