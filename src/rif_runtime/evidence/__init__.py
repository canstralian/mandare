"""Evidence ledger — append-only, versioned, causally linked decision records.

Per ADR-0002, ``decisions.jsonl`` is the canonical replay source. This package
adds an additive v1 envelope around each persisted decision row without
rewriting legacy records:

- ``schema_version`` — selects validation rules during replay
- ``sequence`` — total order when timestamps collide; gap detection
- ``previous_hash`` — causal link to the prior row's content hash
- ``record_hash`` — integrity digest of this row (excluding itself)

Legacy rows (no ``schema_version``) remain readable as plain PolicyDecision
payloads. The v1 chain treats their content hash as the predecessor link so
causality spans the migration boundary without a file rewrite.
"""

from __future__ import annotations

from .ledger import (
    DECISION_SCHEMA_V1,
    EvidenceLedger,
    LedgerChainReport,
    content_hash,
    enrich_decision_row,
)

__all__ = [
    "DECISION_SCHEMA_V1",
    "EvidenceLedger",
    "LedgerChainReport",
    "content_hash",
    "enrich_decision_row",
]
