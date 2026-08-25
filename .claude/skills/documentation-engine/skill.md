---
name: documentation-engine
description: Generate, validate, and maintain RIF documentation from canonical sources while preserving authority, provenance, and evidence.
---

# Documentation Engine

## Mission

Treat documentation as a generated engineering artifact.

Documentation exists to explain authoritative sources.

Documentation never becomes authoritative.

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

## Responsibilities

Generate:

- README
- API Reference
- CLI Reference
- Capability Catalog
- ADR Index
- Architecture Guides
- Release Notes

Never invent implementation details.

---

## Evidence Classification

Every technical statement must be traceable as:

- Confirmed
- Inferred
- Assumption
- Information Required

Missing information is reported rather than fabricated.

---

## Documentation Rules

Generated documentation:

- is reproducible
- includes provenance
- never overwrites Canon
- preserves manual content
- records generation metadata

---

## Validation

Review:

- broken links
- orphaned pages
- undocumented public APIs
- documentation drift
- missing provenance

---

## Success Criteria

Documentation accurately reflects runtime behaviour and remains reproducible from authoritative sources.
