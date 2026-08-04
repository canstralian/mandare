import json
from pathlib import Path
from typing import Any


class JsonlStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def count(self) -> int:
        return len(self.read_all())

    def count_by(self, field: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in self.read_all():
            key = row.get(field, "unknown")
            out[key] = out.get(key, 0) + 1
        return out
