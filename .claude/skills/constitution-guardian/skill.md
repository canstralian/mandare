---
name: constitution-guardian
description: Enforce the RIF Runtime Constitution by validating architectural invariants, governance rules, and authority boundaries before implementation or merge.
---

# Constitution Guardian

## Mission

Protect the long-term integrity of the RIF Runtime.

This skill evaluates proposed changes against the repository's architectural invariants rather than implementation details.

Architecture takes precedence over convenience.

---

## What "Constitution" means here

There is **no `Runtime Constitution` document in this repository.** The name is a shorthand for the architectural invariants listed below.

Authority in this repository is the ladder in [`docs/README.md`](../../../docs/README.md): executable implementation and tests outrank repository configuration, which outranks normative specifications (`spec/`), which outrank architecture and design documents, roadmaps, research, and historical ADRs. Cross-domain contract authority is described in [`spec/README.md`](../../../spec/README.md). Instruction precedence across tools is in [`AGENTS.md`](../../../AGENTS.md).

Do not cite a constitution as though it were a readable artefact, and do not treat this skill's text as outranking code. When an invariant here disagrees with `src/` and `tests/`, the invariant is stale: report it, do not enforce it.

---

## Invariant status

Each invariant below is marked with its current enforcement status, using the vocabulary in `docs/README.md`:

- **Enforced** — present in executable code and covered by tests.
- **Convention** — the codebase follows it, but nothing structurally prevents a violation.
- **Design** — intended contract, not fully implemented.

An invariant marked Convention or Design is a review standard, not a guarantee. Do not describe it in documentation as a shipped property.

---

## Architectural Invariants

### Knowledge — Convention

Generated knowledge is derived and never authoritative. Knowledge projections should be reproducible from their sources. This includes tool-generated agent hint files (`.claude/homunculus/instincts/`, `.claude/identity.json`, `.agents/skills/`), which are inputs, not contracts.

---

### Governance — Convention

`RIFRuntime.execute_capability` (`src/rif_runtime/runtime.py:179`) evaluates policy before execution, records a denial with evidence, admits the capability, and appends completion evidence. That path is **Enforced** and tested (`tests/capabilities/test_governed_execution.py`).

The boundary is the caller, not the kernel: `ExecutionKernel.execute` (`src/rif_runtime/execution/kernel.py:20`) performs no policy evaluation, and `Capability.execute` can be called directly. So "no execution path bypasses policy" is a **Convention** this skill enforces by review, not a structural property.

Reject any new production caller of `ExecutionKernel.execute()` or `Capability.execute()` that does not route through `execute_capability`.

---

### Evidence — Enforced (append-only), Convention (immutability)

Evidence records facts and is written append-only through `JsonlStore` (`src/rif_runtime/storage/jsonl.py`). Append-only writing is Enforced by the store.

Immutability is a **Convention**: nothing prevents another process from rewriting a JSONL file on disk. `src/rif_runtime/audit.py` provides hash-chain primitives that make tampering detectable, not impossible. Do not document evidence as "immutable" or "tamper-proof" — `docs/README.md` bars both words without a narrowly defined, supported claim.

Reject edits-in-place, truncation, or rewrites of an evidence or decision log.

---

### Replay — Enforced (read-only), Convention (determinism)

`src/rif_runtime/replay.py` reconstructs state from `decisions.jsonl` without writing back; read-only replay is Enforced.

Determinism holds for the recorded decision log and is exercised by `tests/test_runtime_restore.py` / `tests/test_runtime_restart.py`. State the property against those tests rather than as an unqualified guarantee.

---

### Resources — Convention

Resources (`src/rif_runtime/resources/`) model addressable state, are treated as value objects, do not perform provider work, and stay provider-independent. This is a review standard, not a runtime-enforced property.

---

### Providers — Convention

Providers execute interactions. Providers never own policy and never become authoritative. A provider credential is configuration; it is not a RIF authorization decision.

---

### Documentation — Convention

Documentation follows the authority ladder in `docs/README.md`. Generated documentation never replaces canonical sources, and a lower-tier statement is never promoted into a higher-tier guarantee.

---

## Authority Ladder

Executable implementation and tests (`src/`, `tests/`)

↓

Repository configuration and workflows

↓

Normative Specifications

↓

Reference Documentation

↓

Architecture Guides

↓

Engineering Guides

↓

Execution Plans

↓

Generated Artifacts

Authority flows downward only.

---

## Review Procedure

For every change determine:

1. Which constitutional principles apply?

2. Which invariants are affected?

3. Does the change weaken architecture?

4. Does the change introduce ambiguity?

5. Should the Constitution evolve instead?

---

## Automatic Rejection Conditions

Reject changes that:

- bypass Governance
- mutate Evidence
- weaken Replay
- create circular dependencies
- introduce hidden side effects
- make generated artifacts authoritative
- place provider logic inside Resources
- place policy inside Providers

---

## Required Output

Every review includes:

Constitutional Summary

Affected Invariants

Risk Assessment

Required ADRs

Recommended Action

---

## Success Criteria

Approve only changes that strengthen or preserve these invariants.

Protect long-term architectural coherence over short-term implementation speed.

An approval from this skill is a review finding, not merge authorization. Ratifying or changing the governance rules themselves is a human decision.
