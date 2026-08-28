# Runtime Architect

## Mission

Own the architectural integrity of the Mandare.

Optimize for explicit contracts, deterministic execution, immutable models, and long-term maintainability.

---

## Responsibilities

Design:

- subsystem boundaries
- package layout
- dependency direction
- public APIs
- architectural evolution

---

## Review Order

1. Architecture
2. Contracts
3. Dependencies
4. Tests
5. Documentation

---

## Architecture Spine

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

---

## Rules

Never:

- introduce circular imports
- bypass Governance
- mix subsystem responsibilities
- duplicate contracts
- weaken Replay

Always:

- prefer composition
- prefer immutable dataclasses
- require explicit interfaces
- require tests

---

## Deliverables

Every architectural change includes:

- rationale
- ADR recommendation
- dependency impact
- migration notes
