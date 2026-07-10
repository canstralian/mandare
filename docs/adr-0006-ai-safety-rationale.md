# ADR-0006: AI Safety Rationale for Runtime Mediation

## Status
Proposed (captured 2026-07-09)

## Context
Agents act at machine speed, can be steered by injected content in the data
they read, and cannot be assumed to have stable intent. "Trust the model" is
not an inspectable or testable property; "trust the runtime" is.

## Decision
The controls in ADR-0003..0005 are the product, not optional hardening. They
follow four principles:

1. **Deny by default** — capability is granted, never assumed; unknown
   actions fail closed
2. **Least privilege, enforced by credentials** — an agent's blast radius is
   bounded by what its tokens can do, not by what its instructions say
3. **Reflexive posture** — accumulated denials automatically tighten the
   system (normal -> elevated -> restricted -> locked), so anomalous behavior
   degrades capability instead of escalating it
4. **Auditability and replay** — every decision is appended to an immutable
   log (`decisions.jsonl`) and can be replayed (`rif replay`) to reconstruct
   governance state

## Consequences
- Every side-effecting agent action is mediated, logged, and reproducible
- Untraceable actions are treated as failures
