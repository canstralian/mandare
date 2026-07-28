"""Evidence Ledger: tamper-evident record of what the runtime did.

Every entry is hash-chained to its predecessor via `audit.append_record`, so a
record cannot be altered or removed without breaking `verify()`. This wires up
the chain primitives in `audit.py`, which existed but were not previously on
any runtime path.

Denials are recorded, not just successes. A refused execution is the most
governance-relevant event the runtime produces — it is what drives posture
escalation and feeds the evolution queue — so the ledger records the decision
before the kernel returns the safe response.

Secrets are redacted on the way in (`security.redact_secrets`): the ledger is
an audit surface, and an API key captured in a payload would otherwise be
persisted in plaintext and hashed into the chain permanently.
"""

from __future__ import annotations

from typing import Any

from .audit import AuditRecord, append_record, verify_chain
from .paths import data_path
from .security import redact_secrets
from .storage.jsonl import JsonlStore

EVIDENCE_FILE = "evidence.jsonl"


class EvidenceLedger:
    def __init__(self, path: str | None = None) -> None:
        self.store = JsonlStore(path or data_path(EVIDENCE_FILE))
        self.chain: list[AuditRecord] = []
        self._restore()

    def _restore(self) -> None:
        """Rebuild the in-memory chain from disk so appends keep chaining.

        Without this, a restarted process would start a fresh chain from
        GENESIS and `verify()` would reject the persisted history.
        """

        for row in self.store.read_all():
            self.chain.append(
                AuditRecord(
                    event_id=row["event_id"],
                    timestamp=row["timestamp"],
                    payload=row["payload"],
                    previous_hash=row["previous_hash"],
                )
            )

    def record(self, event: str, **payload: Any) -> AuditRecord:
        entry = {"event": event, **redact_secrets(payload)}
        record = append_record(self.chain, entry)
        self.chain.append(record)
        self.store.append(
            {
                "event_id": record.event_id,
                "timestamp": record.timestamp,
                "payload": record.payload,
                "previous_hash": record.previous_hash,
                "current_hash": record.current_hash,
            }
        )
        return record

    def verify(self) -> bool:
        return verify_chain(self.chain)

    def entries(self) -> list[AuditRecord]:
        return list(self.chain)

    def head(self) -> str | None:
        return self.chain[-1].current_hash if self.chain else None

    def summary(self) -> dict[str, Any]:
        return {
            "entries": len(self.chain),
            "head": self.head(),
            "intact": self.verify(),
        }
