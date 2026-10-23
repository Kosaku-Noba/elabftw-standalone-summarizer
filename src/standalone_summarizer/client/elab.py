"""Thin wrapper around eLabFTW REST API v2."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterable, List

import requests

from standalone_summarizer.config import AppConfig

logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    id: int
    elabid: str
    title: str
    body: str


class ElabClient:
    """Minimal REST client for polling experiments and posting comments."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.headers.update({"Authorization": config.elab.api_key})

    def fetch_experiments(self, tags: Iterable[str]) -> List[Experiment]:
        tag_list = [t for t in tags if t]
        url = f"{self._config.elab.base_url}/experiments"
        experiments: List[Experiment] = []
        page_size = self._config.elab.page_size
        offset = 0
        pages_fetched = 0
        while pages_fetched < self._config.elab.max_pages:
            # eLabFTW 5.6.15 以降（6.x 系も同様）、一覧APIは既定で列を絞って返し、
            # body / elabid などが欠落する。full=1 で全列を取得する。
            # ページングは v2 共通の offset/limit 方式を用いる。
            # タグは tags[] 配列形式（requests はリスト値を tags[]=... として展開する）。
            params = {
                "tags[]": tag_list,
                "offset": offset,
                "limit": page_size,
                "full": 1,
            }
            logger.debug(
                "Fetching experiments",
                extra={"url": url, "params": params, "offset": offset},
            )
            response = self._session.get(
                url,
                params=params,
                timeout=self._config.elab.timeout_seconds,
                verify=self._config.elab.verify_ssl,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise RuntimeError("Unexpected eLabFTW response structure")
            for item in payload:
                if not isinstance(item, dict):
                    logger.warning("Skipping non-dict experiment entry")
                    continue
                if "id" not in item:
                    logger.warning(
                        "Skipping experiment entry without id",
                        extra={"keys": list(item.keys())},
                    )
                    continue
                experiments.append(
                    Experiment(
                        id=item["id"],
                        elabid=item.get("elabid") or "",
                        title=item.get("title") or "",
                        body=item.get("body") or "",
                    )
                )
            pages_fetched += 1
            if len(payload) < page_size:
                break
            offset += page_size
        return experiments

    def post_comment(self, experiment_id: int, comment: str) -> None:
        payload = {"body": comment}
        url = f"{self._config.elab.base_url}/experiments/{experiment_id}/comments"
        for attempt in range(1, self._config.elab.retry_attempts + 1):
            logger.debug(
                "Posting comment",
                extra={"url": url, "experiment_id": experiment_id, "attempt": attempt},
            )
            response = self._session.post(
                url,
                json=payload,
                timeout=self._config.elab.timeout_seconds,
                verify=self._config.elab.verify_ssl,
            )
            try:
                response.raise_for_status()
                return
            except requests.HTTPError:
                logger.warning(
                    "Failed to post comment",
                    extra={
                        "experiment_id": experiment_id,
                        "status_code": response.status_code,
                        "attempt": attempt,
                    },
                )
                if attempt == self._config.elab.retry_attempts:
                    raise
                self._sleep(self._config.elab.retry_backoff_seconds * attempt)

    @staticmethod
    def _sleep(seconds: float) -> None:
        time.sleep(seconds)
