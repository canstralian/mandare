---
name: constitution-guardian
description: Enforce the RIF Runtime Constitution by validating architectural invariants, governance rules, and authority boundaries before implementation or merge.
---

# Constitution Guardian

## Mission

Protect the long-term integrity of the RIF Runtime.

This skill evaluates proposed changes against the Runtime Constitution rather than implementation details.

Architecture always takes precedence over convenience.

---

## Constitutional Principles

The Runtime Constitution is the highest authority.

No implementation may contradict constitutional rules.

When implementation conflicts with the Constitution, the implementation must change.

---

## Constitutional Invariants

### Knowledge

Generated knowledge is derived.

Generated knowledge is never authoritative.

Knowledge projections must be reproducible.

---

### Governance

Every effectful operation is governed.

Every write operation requires policy evaluation.

Governance decisions are explicit.

---

### Evidence

Evidence records facts.

Evidence is immutable.

Evidence is append-only.

Evidence is replayable.

---

### Replay

Replay verifies execution.

Replay never mutates evidence.

Replay is deterministic.

---

### Resources

Resources model addressable state.

Resources are immutable.

Resources never perform provider work.

Resources remain provider-independent.

---

### Providers

Providers execute interactions.

Providers never own policy.

Providers never become authoritative.

---

### Documentation

Documentation is generated.

Documentation follows the authority ladder.

Generated documentation never replaces canonical sources.

---

## Authority Ladder

Runtime Constitution

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

Approve only changes that strengthen or preserve the Runtime Constitution.

Protect long-term architectural coherence over short-term implementation speed.
