from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from rif_runtime.schemas import PolicyDecision
from rif_runtime.security import sha256_digest
from rif_runtime.storage.jsonl import JsonlStore

# Additive envelope version for decision ledger rows.
DECISION_SCHEMA_V1 = "rif.evidence.decision/v1"

# Fields that are part of the integrity envelope, not the hashed payload.
_ENVELOPE_HASH_FIELDS = frozenset({"record_hash"})


def content_hash(row: dict[str, Any]) -> str:
    """SHA-256 over the row excluding ``record_hash`` (canonical JSON).

    Replay justification: recomputing this digest detects silent mutation of
    any decision or envelope field after append.
    """

    payload = {k: v for k, v in row.items() if k not in _ENVELOPE_HASH_FIELDS}
    return sha256_digest(payload)


def enrich_decision_row(
    decision: PolicyDecision,
    *,
    sequence: int,
    previous_hash: str | None,
) -> dict[str, Any]:
    """Build a JSON-native ledger row with the additive v1 envelope.

    Does not mutate ``decision``. Legacy readers that only know PolicyDecision
    fields can still ``model_validate`` the row (extra keys ignored by default).
    """

    row = decision.model_dump(mode="json")
    row["schema_version"] = DECISION_SCHEMA_V1
    row["sequence"] = sequence
    row["previous_hash"] = previous_hash
    row["record_hash"] = content_hash(row)
    return row


@dataclass
class LedgerChainReport:
    """Result of walking the decision ledger for causal integrity."""

    row_count: int
    legacy_rows: int
    v1_rows: int
    chain_ok: bool
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceLedger:
    """Append-only decision ledger with sequence + hash-chain envelope.

    Wraps ``JsonlStore`` by composition. Thread safety is the caller's
    responsibility (``RIFRuntime`` already serialises writes under ``_lock``).
    """

    def __init__(
        self,
        path: str | Path = "data/decisions.jsonl",
        store: JsonlStore | None = None,
    ) -> None:
        self.path = Path(path)
        self.store = store if store is not None else JsonlStore(self.path)
        self._sequence, self._previous_hash = self._bootstrap()

    def _bootstrap(self) -> tuple[int, str | None]:
        """Recover sequence cursor and tip hash from existing rows.

        Migration policy (no rewrite): legacy rows contribute content hashes
        and count toward the sequence cursor so new v1 rows continue the
        chronological order without colliding sequence numbers.

        Streams the file (constant memory). Corrupt or non-object lines are
        skipped so a damaged tip cannot block ``RIFRuntime`` construction;
        ``ReplayEngine.verify()`` reports those rows explicitly.
        """

        if not self.path.exists():
            return 0, None

        previous: str | None = None
        max_sequence = 0
        # Non-blank row ordinal — same basis as verify_chain()'s enumerate(rows).
        # Physical line numbers inflate the cursor when blank lines appear.
        row_ordinal = 0
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                row_ordinal += 1
                if isinstance(row.get("sequence"), int):
                    max_sequence = max(max_sequence, row["sequence"])
                else:
                    # Legacy row: treat non-blank file order as its sequence.
                    max_sequence = max(max_sequence, row_ordinal)
                previous = (
                    row["record_hash"]
                    if isinstance(row.get("record_hash"), str) and row["record_hash"]
                    else content_hash(row)
                )
        return max_sequence, previous

    @property
    def sequence(self) -> int:
        return self._sequence

    @property
    def previous_hash(self) -> str | None:
        return self._previous_hash

    def append_decision(self, decision: PolicyDecision) -> dict[str, Any]:
        """Persist a decision with v1 envelope; return the written row.

        Sequence and tip hash advance only after a successful durable append so
        a failed write cannot leave the in-memory cursor ahead of the file.
        """

        next_sequence = self._sequence + 1
        row = enrich_decision_row(
            decision,
            sequence=next_sequence,
            previous_hash=self._previous_hash,
        )
        self.store.append(row)
        self._sequence = next_sequence
        self._previous_hash = row["record_hash"]
        return row

    def read_all(self) -> list[dict[str, Any]]:
        return self.store.read_all()

    def export_stable_json(self, *, indent: int | None = 2) -> str:
        """Export the full ledger as stable, sorted-key JSON.

        Ordering is file order (append chronology). Key sorting and
        ``ensure_ascii=True`` keep exports byte-stable across processes for
        the same ledger contents.
        """

        return json.dumps(
            self.read_all(),
            indent=indent,
            sort_keys=True,
            ensure_ascii=True,
            default=str,
        )

    def verify_chain(self) -> LedgerChainReport:
        """Validate chronological hash links without mutating state.

        Streams the ledger file (same blank-skipping, corrupt-skipping ordinal
        basis as ``_bootstrap``). Corrupt lines are reported as errors rather
        than aborting the walk, so a damaged tip remains diagnosable.
        """

        errors: list[str] = []
        legacy = 0
        v1 = 0
        previous: str | None = None
        last_sequence: int | None = None
        row_count = 0
        scan_index = 0

        if self.path.exists():
            with self.path.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    scan_index += 1
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError as exc:
                        errors.append(f"row {scan_index}: JSONDecodeError: {exc}")
                        continue
                    if not isinstance(row, dict):
                        kind = type(row).__name__
                        errors.append(f"row {scan_index}: expected object, got {kind}")
                        continue

                    row_count += 1
                    version = row.get("schema_version")
                    if version == DECISION_SCHEMA_V1:
                        v1 += 1
                        expected_hash = content_hash(row)
                        actual_hash = row.get("record_hash")
                        if actual_hash != expected_hash:
                            errors.append(
                                f"row {scan_index}: record_hash mismatch "
                                f"(expected {expected_hash}, got {actual_hash!r})"
                            )

                        prev = row.get("previous_hash")
                        if prev != previous:
                            errors.append(
                                f"row {scan_index}: previous_hash mismatch "
                                f"(expected {previous!r}, got {prev!r})"
                            )

                        seq = row.get("sequence")
                        if not isinstance(seq, int) or seq < 1:
                            errors.append(f"row {scan_index}: invalid sequence {seq!r}")
                        elif last_sequence is not None and seq <= last_sequence:
                            errors.append(
                                f"row {scan_index}: sequence {seq} not greater than "
                                f"prior sequence {last_sequence}"
                            )
                        else:
                            last_sequence = seq

                        previous = (
                            actual_hash
                            if isinstance(actual_hash, str)
                            else expected_hash
                        )
                    elif version is None:
                        legacy += 1
                        # Legacy: no stored envelope; still advance the causal
                        # tip so a following v1 row can link across migration.
                        # Use valid-row ordinal (row_count), matching _bootstrap.
                        previous = content_hash(row)
                        last_sequence = (
                            row_count
                            if last_sequence is None
                            else max(last_sequence, row_count)
                        )
                    else:
                        errors.append(
                            f"row {scan_index}: unknown schema_version {version!r}"
                        )
                        previous = content_hash(row)

        return LedgerChainReport(
            row_count=row_count,
            legacy_rows=legacy,
            v1_rows=v1,
            chain_ok=not errors,
            errors=errors,
        )
