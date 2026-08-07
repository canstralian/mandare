# spec/evidence

Contract for evidence records: what must be captured, in what shape, for a runtime
action to be independently verifiable later.

`observation_event.schema.json` is migrated unchanged from
`contracts/rif_familiar/observation_event.schema.json` — it defines a
privacy-redacted, chained passive observation event, and is the seed contract for
this directory.

# Runtime implementation:
# - Hash-chain primitives: `src/rif_runtime/audit.py`
# - Decision evidence ledger (ADR-0002 canonical replay source):
#   `src/rif_runtime/evidence/` — additive v1 envelope on `decisions.jsonl`
#   (`schema_version`, `sequence`, `previous_hash`, `record_hash`) with
#   legacy-row readability, `EvidenceLedger.verify_chain()`, and stable JSON
#   export (`rif evidence-export`, `GET /v1/evidence/export`).

## Decision ledger v1 field justifications (replay)

| Field | Replay use |
|---|---|
| `schema_version` | Selects validation rules; absent ⇒ legacy PolicyDecision-only row |
| `sequence` | Total order when timestamps collide; detects gaps / reordering |
| `previous_hash` | Causal link to prior row content hash (spans legacy→v1) |
| `record_hash` | Detects silent mutation of any hashed field after append |

Migration: **no file rewrite**. New appends write v1; readers accept both.

## Next slice
Per ADR-0008, evidence should become a system (ledger, recorder, validators,
provenance, exporter, hashing, signing) rather than a single writer. Define
contracts for each of those pieces here as the corresponding runtime modules are
built, rather than all at once. Metasploit `EvidenceEvent` signing remains a
separate HMAC surface (`mcp/metasploit.py`) and is intentionally unchanged so
existing signatures keep verifying.
