# spec/capability

Contract for declaring what a capability (agent, device, or skill) is authorized to
do: its authority set, resource pinning, and budgets.

`capability_manifest.schema.json` is a byte-identical **copy** of
`contracts/rif_familiar/capability_manifest.schema.json` — the first concrete
instance of this contract, originally scoped to the RIF Familiar / Field Observer
device. ADR-0008 calls for migrating existing contracts rather than duplicating
them; what landed is a copy with the original left in place, so both exist. See
`spec/README.md` and `docs/SPECS_DOCS_AUDIT.md` (H3).

Runtime implementation: none yet. The schema has no consumer at all in this
location. `tests/test_rif_familiar_contracts.py` validates the
`contracts/rif_familiar/` copy against `fixtures/rif_familiar/` — **this copy is
untested** and can drift from the tested original without anything failing.

Note that `src/rif_runtime/mcp/capabilities.py` — despite the name — does **not**
implement this contract. It is the Metasploit MCP tool taxonomy
(`CONTRACT_VERSION = "msf-governance/v1"`), classifying tool capabilities by
authority; this schema describes a device's declared authority set, budgets, and
relay policy. The two are unrelated. A general capability-manifest contract for
the runtime (as opposed to the RIF Familiar device) is still to be written.

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
