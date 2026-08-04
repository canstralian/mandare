from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonStore:
    def __init__(self, path: str, default: dict[str, Any]):
        """
        Initialize a JSON store at the specified path.
        
        Parameters:
            path (str): File path used to persist the JSON data.
            default (dict[str, Any]): Data written when the file does not exist.
        """
        self.path = Path(path)
        self.default = default
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.write(default)

    def read(self) -> dict[str, Any]:
        """
        Read and parse the JSON data stored in the file.
        
        Returns:
            dict[str, Any]: The parsed JSON object.
        """
        data: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        return data

    def write(self, data: dict[str, Any]) -> None:
        """
        Persist JSON data to the configured file.
        """
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)
