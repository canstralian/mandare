from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

JsonlRecord = dict[str, Any]


class JsonlStore:
    """Append-only JSONL log.

    Reads walk the whole file, so callers summarising several fields should
    prefer :meth:`summarise` over repeated ``count``/``count_by`` calls, each
    of which re-reads the log from disk.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: JsonlRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def read_all(self) -> list[JsonlRecord]:
        if not self.path.exists():
            return []
        rows: list[JsonlRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def count(self) -> int:
        return len(self.read_all())

    def count_by(self, field: str) -> dict[str, int]:
        return self.summarise(field)[field]

    def summarise(self, *fields: str) -> dict[str, dict[str, int]]:
        """Tally every requested field in one pass over the log."""

        tallies: dict[str, Counter[str]] = {field: Counter() for field in fields}
        for row in self.read_all():
            for field, tally in tallies.items():
                tally[str(row.get(field, "unknown"))] += 1
        return {field: dict(tally) for field, tally in tallies.items()}
