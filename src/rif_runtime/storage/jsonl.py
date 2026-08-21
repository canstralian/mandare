import json
from pathlib import Path
from typing import Any

from ..audit import GENESIS_HASH, AuditRecord, utc_now_iso
from ..security import normalize_for_json

CHAIN_KEY = "_chain"


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


class ChainVerification:
    """Outcome of verifying a hash-chained log.

    ``verified`` covers the chained portion only. ``unchained_leading`` counts
    rows written before chaining was introduced: they are reported, never
    silently treated as verified.
    """

    def __init__(
        self,
        verified: bool,
        chained_rows: int,
        unchained_leading: int,
        broken_at: int | None = None,
    ) -> None:
        self.verified = verified
        self.chained_rows = chained_rows
        self.unchained_leading = unchained_leading
        self.broken_at = broken_at

    def as_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "chained_rows": self.chained_rows,
            "unchained_leading": self.unchained_leading,
            "broken_at": self.broken_at,
        }


class HashChainedJsonlStore(JsonlStore):
    """Append-only JSONL whose rows are linked by a SHA-256 hash chain.

    Each row carries a ``_chain`` envelope holding the record's ``event_id``,
    ``timestamp``, the ``previous_hash`` it was written against, and its own
    ``current_hash``. Editing any earlier row changes its hash and breaks every
    link after it, which is what makes the log tamper-evident rather than
    merely append-only.

    The payload is normalised (``security.normalize_for_json``) *before* being
    both hashed and written, so the bytes on disk are the bytes that were
    hashed. Writing via ``json.dumps(default=str)`` instead would serialise a
    datetime as ``"... 09:55:37+00:00"`` while the digest covered
    ``"...T09:55:37+00:00"``, and verification could never succeed.

    Single-writer assumption: the last hash is cached after the first read, so
    a second *process* appending to the same file will fork the chain. That is
    the same constraint ``JsonlStore`` already has -- neither takes a file
    lock. Within a process, ``RIFRuntime`` serialises appends under its lock.
    """

    def __init__(self, path: str | Path) -> None:
        super().__init__(path)
        self._last_hash: str | None = None

    def _tail_hash(self) -> str:
        """Hash the next row must link to, read from disk on first use."""
        if self._last_hash is None:
            self._last_hash = GENESIS_HASH
            for row in self.read_all():
                chain = row.get(CHAIN_KEY)
                if isinstance(chain, dict) and "current_hash" in chain:
                    self._last_hash = str(chain["current_hash"])
        return self._last_hash

    def append(self, record: dict[str, Any]) -> None:
        payload = normalize_for_json(record)
        entry = AuditRecord(
            event_id=AuditRecord.new_event_id(),
            timestamp=utc_now_iso(),
            payload=payload,
            previous_hash=self._tail_hash(),
        )
        row = dict(payload)
        row[CHAIN_KEY] = {
            "event_id": entry.event_id,
            "timestamp": entry.timestamp,
            "previous_hash": entry.previous_hash,
            "current_hash": entry.current_hash,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        self._last_hash = entry.current_hash

    def verify(self) -> ChainVerification:
        """Recompute every link and report where, if anywhere, it breaks."""
        rows = self.read_all()
        previous_hash = GENESIS_HASH
        chained = 0
        unchained_leading = 0
        started = False

        for index, row in enumerate(rows):
            chain = row.get(CHAIN_KEY)
            if not isinstance(chain, dict):
                if started:
                    # An unchained row after chaining began: either a rollback
                    # to the plain store or a row spliced in by hand.
                    return ChainVerification(False, chained, unchained_leading, index)
                unchained_leading += 1
                continue

            started = True
            payload = {key: value for key, value in row.items() if key != CHAIN_KEY}
            recomputed = AuditRecord(
                event_id=str(chain.get("event_id", "")),
                timestamp=str(chain.get("timestamp", "")),
                payload=payload,
                previous_hash=str(chain.get("previous_hash", "")),
            )
            linked = chain.get("previous_hash") == previous_hash
            intact = chain.get("current_hash") == recomputed.current_hash
            if not (linked and intact):
                return ChainVerification(False, chained, unchained_leading, index)

            previous_hash = str(chain["current_hash"])
            chained += 1

        return ChainVerification(True, chained, unchained_leading)
