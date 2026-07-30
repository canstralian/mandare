from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class JsonStore:
    """Whole-file JSON state with an atomic replace on write."""

    def __init__(self, path: str | Path, default: dict[str, Any]) -> None:
        self.path = Path(path)
        self.default = default
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.write(default)

    def read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def write(self, data: dict[str, Any]) -> None:
        # Unique temp file per write, in the destination directory so the
        # replace stays on one filesystem. A shared fixed name (path + ".tmp")
        # lets concurrent writers delete each other's temp file mid-rename,
        # which surfaces as FileNotFoundError rather than a lost update.
        fd, tmp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
            os.replace(tmp_name, self.path)
        except BaseException:
            # Never leave a partial temp file behind on failure.
            Path(tmp_name).unlink(missing_ok=True)
            raise
