import json
from pathlib import Path
from typing import Any


class JsonlStore:
    def __init__(self, path: str | Path) -> None:
        """Initialize a JSON Lines store at the specified path.
        
        Parameters:
        	path (str | Path): Path to the JSON Lines file.
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> None:
        """
        Append a record to the JSON Lines file.
        
        Parameters:
        	record (dict[str, Any]): The record to serialize and append.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        """
        Read all records from the JSON Lines file.
        
        Returns:
        	list[dict[str, Any]]: The parsed records, or an empty list when the file does not exist.
        """
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def count(self) -> int:
        """Count the records stored in the JSON Lines file.
        
        Returns:
        	int: The number of stored records.
        """
        return len(self.read_all())

    def count_by(self, field: str) -> dict[str, int]:
        """
        Count records grouped by the value of a specified field.
        
        Parameters:
        	field (str): The field whose values determine the groups.
        
        Returns:
        	dict[str, int]: A mapping of field values to their occurrence counts, using "unknown" for records without the field.
        """
        out: dict[str, int] = {}
        for row in self.read_all():
            key = row.get(field, "unknown")
            out[key] = out.get(key, 0) + 1
        return out
