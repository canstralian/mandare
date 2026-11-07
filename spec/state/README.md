# spec/state

Contract for structured runtime state — the shared state every agent reasons over,
modeled explicitly instead of one `runtime_state.json` blob.

**Placeholder** — no schema yet. Per ADR-0008, this should decompose into
objectives, decisions, constraints, work items, risks, memories, and budgets.

## Next slice
No `runtime_state.json` exists in this repository — the name is ADR-0008's shorthand
for the monolithic-blob shape to be avoided, not a file to inspect. The state the
runtime actually tracks today is spread across the four `JsonlStore` logs owned by
`RIFRuntime` — `data/decisions.jsonl`, `data/posture_history.jsonl`,
`data/metasploit_evidence.jsonl`, and `data/capability_evidence.jsonl`
(`runtime.py`) — plus `data/policies.json` behind
`PolicyStore`, the Supabase `execution_runs` / `evidence_ledger` tables written by
`integrations/supabase.py`, and the in-memory `GovernanceGraph` and
`TelemetryStore`. Extract one schema per concern above, starting with whichever
concern those surfaces already model most concretely.
