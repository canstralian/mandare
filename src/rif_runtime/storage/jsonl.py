"""Storage backend using SQLite with WAL mode.

Replaces the original JSONL flat-file writer while preserving the public API.
Thread-safe, transactional, and multi-process safe via WAL journal mode.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Any


class StorageWriter:
    """Thread-safe append-only store backed by SQLite with WAL mode.

    The on-disk path swaps the original `.jsonl` extension for `.db` internally,
    but the public ``path`` property returns the original config-compatible value.
    """

    def __init__(self, path: str | Path) -> None:
        self._public_path = Path(path)
        # Swap .jsonl for .db internally; keep public path for config compat
        self._db_path = self._public_path.with_suffix(".db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._connect()

    def _connect(self) -> None:
        """Open a SQLite connection with WAL mode and create schema."""
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS records ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  data TEXT NOT NULL"
            ")"
        )
        self._conn.commit()

    def _ensure_conn(self) -> sqlite3.Connection:
        """Return the active connection, reconnecting if closed."""
        if self._conn is None:
            self._connect()
        assert self._conn is not None  # noqa: S101
        return self._conn

    @property
    def path(self) -> Path:
        """Public path (config-compatible, preserves original extension)."""
        return self._public_path

    def append(self, record: dict[str, Any]) -> None:
        """Insert a record atomically with rollback on failure."""
        serialized = json.dumps(record, default=str)
        with self._lock:
            conn = self._ensure_conn()
            try:
                conn.execute("INSERT INTO records (data) VALUES (?)", (serialized,))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def iter_records(self) -> Iterator[dict[str, Any]]:
        """Stream all rows as dicts in insertion order."""
        with self._lock:
            conn = self._ensure_conn()
            cursor = conn.execute("SELECT data FROM records ORDER BY id")
            rows: list[tuple[Any, ...]] = cursor.fetchall()
        for (row_data,) in rows:
            yield json.loads(row_data)

    def read_all(self) -> list[dict[str, Any]]:
        """Read all records. Backwards-compatible with the original API."""
        return list(self.iter_records())

    def count(self) -> int:
        """Return total row count efficiently via SQL COUNT."""
        with self._lock:
            conn = self._ensure_conn()
            cursor = conn.execute("SELECT COUNT(*) FROM records")
            row = cursor.fetchone()
            assert row is not None  # noqa: S101
            result: int = row[0]
            return result

    def count_by(self, field: str) -> dict[str, int]:
        """Count records grouped by a field value. Backwards-compatible."""
        out: dict[str, int] = {}
        for row in self.iter_records():
            key = str(row.get(field, "unknown"))
            out[key] = out.get(key, 0) + 1
        return out

    def tail(self, n: int) -> list[dict[str, Any]]:
        """Return the last *n* records efficiently using SQL LIMIT."""
        with self._lock:
            conn = self._ensure_conn()
            cursor = conn.execute(
                "SELECT data FROM records ORDER BY id DESC LIMIT ?", (n,)
            )
            rows: list[tuple[Any, ...]] = cursor.fetchall()
        return [json.loads(r[0]) for r in reversed(rows)]

    def export_jsonl(self) -> str:
        """Export all records as JSONL-formatted string for audit log consumers."""
        lines: list[str] = []
        for record in self.iter_records():
            lines.append(json.dumps(record, default=str))
        return "\n".join(lines) + ("\n" if lines else "")

    def close(self) -> None:
        """Close the underlying database connection."""
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __enter__(self) -> StorageWriter:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager and close connection."""
        self.close()


# Backwards compatibility alias — original class name
JsonlStore = StorageWriter
