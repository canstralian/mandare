from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonStore:
    def __init__(self, path: str, default: dict[str, Any]):
        self.path = Path(path)
        self.default = default
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.write(default)

    def read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)
