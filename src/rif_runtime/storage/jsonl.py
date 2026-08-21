import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any

try:  # POSIX only; absent on Windows.
    import fcntl
except ImportError:  # pragma: no cover - platform dependent
    fcntl = None  # type: ignore[assignment]

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
        """Read all nonblank JSON records stored in the file.
        
        Returns:
        	list[dict[str, Any]]: The parsed records, or an empty list if the file does not exist.
        
        Raises:
        	json.JSONDecodeError: If a nonblank line is not valid JSON.
        """
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def count(self, rows: list[dict[str, Any]] | None = None) -> int:
        """Count records in the store or in a provided snapshot.
        
        Parameters:
        	rows (list[dict[str, Any]] | None): Optional records to count instead of reading from the store.
        
        Returns:
        	int: The number of records.
        """
        return len(self.read_all() if rows is None else rows)

    def count_by(
        self, field: str, rows: list[dict[str, Any]] | None = None
    ) -> dict[str, int]:
        """Count occurrences of each value for a field in the log or a supplied snapshot.
        
        Parameters:
            field (str): Name of the field to tally.
            rows (list[dict[str, Any]] | None): Optional pre-read rows to summarize.
        
        Returns:
            dict[str, int]: Counts keyed by field value, using ``"unknown"`` for missing fields.
        """
        out: dict[str, int] = {}
        for row in self.read_all() if rows is None else rows:
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
        """
        Initialize the chain verification result.
        
        Parameters:
            verified (bool): Whether all chained rows pass verification.
            chained_rows (int): Number of rows included in the verified chain.
            unchained_leading (int): Number of unchained rows preceding the chain.
            broken_at (int | None): Index of the first invalid row, if verification failed.
        """
        self.verified = verified
        self.chained_rows = chained_rows
        self.unchained_leading = unchained_leading
        self.broken_at = broken_at

    def as_dict(self) -> dict[str, Any]:
        """Return the chain verification result as a dictionary.
        
        Returns:
            dict[str, Any]: Verification status, row counts, and the index of any broken row.
        """
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

    Concurrent writers are the case this has to get right. ``rif check`` builds
    its own ``RIFRuntime`` against the same ``RIF_DATA_DIR`` as a running
    ``rif serve``, so two processes appending to one log is ordinary use, not an
    edge case. Caching the tail hash for the object's lifetime forked the chain
    the moment that happened, and a forked chain reports ``verified: false``
    forever -- indistinguishable from tampering, which is the one thing this
    class exists to detect.

    So the tail is read back under an exclusive ``flock`` on every append, and
    the link is computed inside that lock. The read seeks from the end rather
    than parsing the file, so it stays cheap as the log grows. Within a process
    ``RIFRuntime`` also serialises appends under its own lock; this covers the
    cross-process case that one cannot.

    ``fcntl`` is POSIX-only. Without it (Windows) the lock degrades to a no-op
    and the single-writer assumption returns; the runtime targets Linux.
    """

    #: Bytes to read back when locating the final line. One row is ~1 KB.
    _TAIL_WINDOW = 65536

    @contextmanager
    def _locked(self) -> Iterator[IO[str]]:
        """Provides an append-capable file handle while holding an exclusive advisory lock.
        
        The handle is flushed before the lock is released so subsequent writers can read
        the latest contents."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield handle
            finally:
                # Not fsync: the page cache is enough for another *process* to
                # read what was written. Surviving a machine crash is a
                # different (and much more expensive) guarantee, and the log
                # does not claim it.
                handle.flush()
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _tail_hash(self, handle: IO[str]) -> str:
        """Hash the next row must link to, read from the end of the open file.

        Must be called with the lock held: the value is only true for as long
        as no other writer can append.
        """
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        if size == 0:
            return GENESIS_HASH

        handle.seek(max(0, size - self._TAIL_WINDOW))
        lines = [line for line in handle.read().splitlines() if line.strip()]
        if not lines:
            return GENESIS_HASH

        try:
            chain = json.loads(lines[-1]).get(CHAIN_KEY)
        except json.JSONDecodeError:
            return GENESIS_HASH
        if isinstance(chain, dict) and "current_hash" in chain:
            return str(chain["current_hash"])
        # Final row predates chaining: start the chain from genesis. verify()
        # counts those rows as unchained_leading rather than verified.
        return GENESIS_HASH

    def append(self, record: dict[str, Any]) -> None:
        """Append a record with linked audit metadata to the JSONL store.
        
        Parameters:
            record (dict[str, Any]): Payload to append to the store.
        """
        payload = normalize_for_json(record)
        with self._locked() as handle:
            entry = AuditRecord(
                event_id=AuditRecord.new_event_id(),
                timestamp=utc_now_iso(),
                payload=payload,
                previous_hash=self._tail_hash(handle),
            )
            row = dict(payload)
            row[CHAIN_KEY] = {
                "event_id": entry.event_id,
                "timestamp": entry.timestamp,
                "previous_hash": entry.previous_hash,
                "current_hash": entry.current_hash,
            }
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(row) + "\n")

    def verify(self, rows: list[dict[str, Any]] | None = None) -> ChainVerification:
        """
        Verify the integrity and ordering of the store's hash chain.
        
        Parameters:
            rows (list[dict[str, Any]] | None): Optional preloaded rows to verify instead of reading the store.
        
        Returns:
            ChainVerification: Verification status, chained and leading unchained row counts, and the first broken row index when applicable.
        """
        rows = self.read_all() if rows is None else rows
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
