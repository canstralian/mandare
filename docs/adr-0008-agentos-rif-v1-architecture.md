# ADR-0008: AgentOS/RIF v1.0 — Governed Runtime Architecture

## Status
Accepted (direction) — implementation to proceed incrementally, tracked as separate work items.

## Context
`rif-runtime` today ships a working governance-first runtime (policy → decision →
reflexive loop → posture → governance graph → persistent memory → audit API), but
specification, runtime code, and documentation are interwoven in `src/rif_runtime/`
and `docs/`. There is no first-class packaging for capabilities (skills/plugins), no
dedicated control plane, and evidence/replay are single modules rather than systems.

## Decision
Evolve the repository from a runtime implementation into a **specification +
reference implementation** pair, under one guiding principle:

> AgentOS/RIF is not an agent framework — it is a governed runtime for executable
> capabilities.

Concretely, adopt the following structural boundaries:

- **`spec/`** — versioned contracts (skill, governance, evidence, replay, state,
  capability) that any runtime (Python, Rust, Go, .NET) can conform to. Runtime code
  implements these contracts; it does not define them.
- **`control_plane/`** — dedicated coordination layer (`runtime`, `lifecycle`,
  `budget`, `coordinator`, `checkpoints`, `recovery`) as the seam between
  capabilities, governance, and execution.
- **Capability packaging** — `skills/` (self-contained, versioned, testable units)
  and `plugins/` (bundles of skills + policies + schemas + MCP config + agent
  definitions) as first-class, not incidental, directories.
- **Governance expansion** — admission, policy engine, permissions, approvals,
  trust, signatures, sandboxing, provenance as separate modules supporting
  supply-chain validation.
- **Evidence and replay as systems**, not single files — ledger/recorder/validators/
  provenance/exporter/hashing/signing for evidence; capture/runner/diff/comparator/
  timeline/report/deterministic for replay.
- **Structured runtime state** — objectives, decisions, constraints, work items,
  risks, memories, budgets as explicit modules instead of one `runtime_state.json`.
- **Governed integrations** — adapters (github, notion, jira, slack, azure, openai,
  anthropic, mcp, filesystem) expose governed capabilities, not raw APIs.
- **Continuous evaluation** — benchmarks, rubrics, judges, regression, scorecards.
- **Explicit repository lifecycle** as an observable, auditable state machine: Intent
  → Planning → Capability Resolution → Governance → Budget Allocation → Execution →
  Evidence Capture → Replay Verification → Documentation → Release.
- **Docs as an engineering handbook**, not a flat folder: architecture, concepts,
  runtime, governance, evidence, replay, capabilities, plugins, skills,
  integrations, tutorials, operations, reference, adr, diagrams.

## Consequences
- This is a large surface area. It is **not** a single PR — it is a sequence of
  small, independently mergeable slices (e.g., `spec/` skeleton first, since
  everything else conforms to it).
- Existing `contracts/rif_familiar/` schemas are the seed for `spec/capability/` and
  `spec/skill/` — migrate rather than duplicate.
- Existing `src/rif_runtime/governance/`, `audit.py`, `replay.py` become the first
  implementations of the new `spec/` contracts, not replacements to throw away.
- Each future slice should land as its own PR with evidence (tests / docs) attached,
  per the lifecycle state machine above.

## First slice (this PR)
Record this decision. No runtime code changes. Next slice: scaffold `spec/`
top-level layout (`spec/skill/`, `spec/governance/`, `spec/evidence/`,
`spec/replay/`, `spec/state/`, `spec/capability/`), each with a `README.md` stating
what it contracts and pointing at the current `contracts/rif_familiar/*.schema.json`
as the first migrated content.
