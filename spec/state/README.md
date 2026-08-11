# spec/state

Contract for structured runtime state — the shared state every agent reasons over,
modeled explicitly instead of one `runtime_state.json` blob.

**Placeholder** — no schema yet. Per ADR-0008, this should decompose into
objectives, decisions, constraints, work items, risks, memories, and budgets.

## Next slice
Inspect the current `runtime_state.json` shape (if/where it exists in the runtime)
and extract one schema per concern above, starting with whichever concern the
runtime already tracks most concretely.
