# spec/evidence

Contract for evidence records: what must be captured, in what shape, for a runtime
action to be independently verifiable later.

`observation_event.schema.json` is migrated unchanged from
`contracts/rif_familiar/observation_event.schema.json` — it defines a
privacy-redacted, chained passive observation event, and is the seed contract for
this directory.

Runtime implementation: `src/mandare/audit.py`.

## Next slice
Per ADR-0008, evidence should become a system (ledger, recorder, validators,
provenance, exporter, hashing, signing) rather than a single writer. Define
contracts for each of those pieces here as the corresponding runtime modules are
built, rather than all at once.
