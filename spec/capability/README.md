# spec/capability

Contract for declaring what a capability (agent, device, or skill) is authorized to
do: its authority set, resource pinning, and budgets.

`capability_manifest.schema.json` is migrated unchanged from
`contracts/rif_familiar/capability_manifest.schema.json` — the first concrete
instance of this contract, originally scoped to the RIF Familiar / Field Observer
device. It seeds this directory rather than being rewritten, per ADR-0008's
instruction to migrate existing contracts rather than duplicate them.

Runtime implementation: `src/rif_runtime/mcp/capabilities.py`.

## Open contract question — snapshot binding

The manifest above describes a capability set that is **declared and pinned at
registration**. It does not cover a capability catalog **observed at decision
time** from a remote MCP server, which since MCP `2026-07-28` is a cacheable,
mutable artifact (`ttlMs`, `cacheScope`) carrying no stability guarantee.

`docs/spec-review-capability-snapshot-authority.md` (Track B, Draft) holds the
normative treatment: what observation becomes authoritative for a unit of work,
and what governs its replacement. Its current resolution is that a
`capability_snapshot_id` binds to a `Decision`, not to a `Run` or an `Execution`.

No implementation is authorized until that review is approved.
