---
name: run-rif-runtime
description: Develop, review, and evolve Mandare while preserving architectural contracts, governance, evidence, replay, and quality standards.
---

# Mandare Skill

## Mission

You are an engineering agent for Mandare.

Your objective is to improve the runtime while preserving its architectural integrity.

Optimize for correctness, maintainability, determinism, and explicit contracts.

---

## Architecture

Resources => Providers => Knowledge => Documentation

Execution => Governance => Evidence => Replay

Responsibilities flow downward.

Dependencies never flow upward.

---

## Core Invariants

### Resources

- Model addressable state.
- Immutable.
- Provider-independent.

### Providers

- Execute interactions.
- Never contain policy.

### Knowledge

- Derived.
- Never authoritative.
- Reproducible.

### Documentation

- Rendered from knowledge.
- Never canonical.

### Governance

Every effectful operation requires authorization.

### Evidence

Append-only.

Immutable.

### Replay

Verifies execution.

Never mutates history.

---

## Engineering Rules

Prefer:

- Composition
- Frozen dataclasses
- Explicit interfaces
- Dependency inversion
- Deterministic execution

Avoid:

- Circular imports
- Hidden state
- Side effects during import
- Implicit behaviour

---

## Python Standards

Every public API requires:

- Type hints
- Docstrings
- Tests

Follow the Zen of Python.

---

## Repository Layout

src/

tests/

docs/

contracts/

spec/

scripts/

Every new runtime package requires a matching test package.

---

## Documentation Hierarchy

Runtime Constitution

=>

Normative Specifications

=>

Reference Documentation

=>

Generated Documentation

Generated documentation never becomes authoritative.

---

## Quality Gate

Before completing work:

python -m compileall src

pytest

mypy src

ruff check src tests

---

## Review Checklist

Reject changes that:

- introduce circular dependencies
- bypass governance
- weaken replay
- weaken evidence
- duplicate contracts
- violate subsystem boundaries

---

## Workflow

Understand

=>

Design

=>

Contracts

=>

Implementation

=>

Tests

=>

Documentation

=>

Quality Gate

=>

Review

---

## Success Criteria

Every contribution should:

- preserve architecture
- improve maintainability
- strengthen determinism
- increase test coverage
- leave the repository releasable
