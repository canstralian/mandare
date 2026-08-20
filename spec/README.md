# spec/

Versioned contracts for AgentOS/RIF. Everything here defines a boundary that any
runtime (this Python implementation, or a future Rust/Go/.NET one) must conform to.
The runtime under `src/rif_runtime/` implements these contracts; it does not define
them — schema and contract changes land here first, then flow into the
implementation.

Per ADR-0008 (`docs/adr-0008-agentos-rif-v1-architecture.md`), the six contract
domains are:

| Domain | Status | Contents |
| --- | --- | --- |
| `capability/` | seeded | Capability manifest schema (migrated from `contracts/rif_familiar/`) |
| `governance/` | seeded | Posture decision schema (migrated from `contracts/rif_familiar/`) |
| `evidence/` | seeded | Observation event schema (migrated from `contracts/rif_familiar/`) |
| `replay/` | placeholder | Replay contract not yet extracted from `src/rif_runtime/replay.py` |
| `skill/` | placeholder | Skill package format (`SKILL.md` + `skill.yaml` + tests) not yet formalized |
| `state/` | placeholder | Structured runtime state contract not yet extracted from `runtime_state.json` |

Beyond the six original domains, governed-integration contracts also live here:

| Domain | Status | Contents |
| --- | --- | --- |
| `mcp/` | drafted | MCP server framework governance contract (`SPEC.md`): authority tiers, ordered decision procedure, destructive-action hard gate, evaluation scorecard — generalizes `src/rif_runtime/mcp/metasploit.py` |

`contracts/rif_familiar/` is left in place unchanged for this slice — it is the
device-facing (RIF Familiar / Field Observer) contract set and is the origin of the
schemas seeded into `capability/`, `governance/`, and `evidence/` above. A later
slice should decide whether `contracts/rif_familiar/` re-exports from `spec/` or is
retired in favor of it; that decision is out of scope here.

## Specification reviews in flight

Contract changes that cross more than one domain are worked as specification
reviews under `docs/` before landing as schemas here. Builder work on a domain is
held while a review governing it is open.

| Review | Governs | Status |
| --- | --- | --- |
| `docs/spec-review-identity-spine-migration.md` | Identity hierarchy, `Run` as aggregate root | Approved Pending Governance Completion |
| `docs/spec-review-capability-snapshot-authority.md` | `capability/`, `replay/`, `mcp/` — what capability observation authorizes a unit of work | Draft |

## Next slices
- Extract a `replay/` contract from `src/rif_runtime/replay.py`, including the
  replay-is-not-recovery constraint stated in the capability-snapshot review §6.
- Extract a `state/` contract from the current `runtime_state.json` shape.
- Define the `skill/` package format contract (`SKILL.md` + `skill.yaml` schema).
