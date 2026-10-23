"""State tracking primitives."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple


@dataclass
class ProcessedEntry:
    experiment_id: int
    elabid: str
    body_hash: str


class StateStore:
    """Simple SQLite backed store to prevent duplicate processing."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path("./data/state.db")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed (
                    experiment_id INTEGER PRIMARY KEY,
                    elabid TEXT NOT NULL,
                    body_hash TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )

    def mark_processed(self, entry: ProcessedEntry, metadata: dict[str, str] | None = None) -> None:
        payload = json.dumps(metadata or {})
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO processed (experiment_id, elabid, body_hash, metadata) VALUES (?, ?, ?, ?)",
                (entry.experiment_id, entry.elabid, entry.body_hash, payload),
            )

    def has_changed(self, entry: ProcessedEntry) -> bool:
        cursor = self._conn.execute(
            "SELECT body_hash FROM processed WHERE experiment_id = ?",
            (entry.experiment_id,),
        )
        row = cursor.fetchone()
        return row is None or row[0] != entry.body_hash

    @staticmethod
    def compute_body_hash(body: str) -> str:
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def iter_all(self) -> Iterable[Tuple[int, str, str]]:
        cursor = self._conn.execute(
            "SELECT experiment_id, elabid, body_hash FROM processed"
        )
        yield from cursor.fetchall()
