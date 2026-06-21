# ADR-0002: Replayable Governance Memory

## Status
Accepted

## Context
Audit logs were previously write-only.

## Decision
Audit events become the canonical replay source for reconstructing governance state.

## Consequences
- Deterministic recovery
- Auditable state reconstruction
- Replay validation becomes possible
