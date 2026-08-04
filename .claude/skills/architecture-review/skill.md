---
name: architecture-review
description: Review proposed changes against the RIF Runtime architecture, invariants, dependency rules, and long-term evolution.
---

# Architecture Review Skill

## Mission

Review every proposed change for architectural correctness before implementation.

Optimize for long-term maintainability rather than local convenience.

---

## Review Order

1. Architecture
2. Contracts
3. Dependencies
4. Determinism
5. Maintainability
6. Performance

Never optimize performance by violating architecture.

---

## Runtime Spine

Resources
↓

Providers
↓

Knowledge
↓

Documentation

Execution
↓

Governance
↓

Evidence
↓

Replay

Every component belongs to exactly one subsystem.

---

## Dependency Rules

Allowed

Resources → Providers

Providers → Knowledge

Knowledge → Documentation

Execution → Governance

Governance → Evidence

Evidence → Replay

Forbidden

Documentation → Knowledge

Providers → Resources

Replay → Governance

Resources → Documentation

Knowledge → Providers

---

## Review Questions

For every proposed change ask:

• Which subsystem owns this?

• Does it introduce a new dependency?

• Can the dependency be inverted?

• Does it increase coupling?

• Does it preserve determinism?

• Does it require a new ADR?

---

## Architecture Smells

Flag immediately:

- circular imports
- singleton abuse
- mutable global state
- duplicated contracts
- hidden dependencies
- undocumented invariants
- provider-specific logic in resources
- business logic in providers

---

## Resource Rules

Resources describe state.

Resources never execute work.

Resources never call providers.

Resources are immutable.

---

## Provider Rules

Providers perform interactions.

Providers never implement policy.

Providers expose stable contracts.

---

## Knowledge Rules

Knowledge interprets snapshots.

Knowledge is reproducible.

Knowledge is derived.

Knowledge is never authoritative.

---

## Documentation Rules

Documentation renders knowledge.

Documentation never replaces source truth.

Generated documentation must remain reproducible.

---

## Governance Rules

Every effectful operation passes through Governance.

No bypasses.

No hidden writes.

---

## Evidence Rules

Evidence is append-only.

Evidence records facts.

Evidence is immutable.

---

## Replay Rules

Replay validates execution.

Replay never mutates history.

---

## Required Outputs

Every review produces:

Architecture Summary

Dependency Impact

Risk Assessment

Suggested Improvements

ADR Recommendation (if required)

---

## Success Criteria

Approve only changes that strengthen the architecture and preserve subsystem boundaries.

Reject shortcuts that create future maintenance debt.
