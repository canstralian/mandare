# spec/governance

Contract for governance decisions: how the runtime evaluates policy and posture,
and what a decision record must contain to be auditable.

`posture_decision.schema.json` is migrated unchanged from
`contracts/rif_familiar/posture_decision.schema.json` — it defines the RIF
posture-decision shape (allow/deny/adapt + rationale) and is the seed contract for
this directory.

Runtime implementation: `src/rif_runtime/governance/posture.py`,
`src/rif_runtime/governance/reflexive.py`, `src/rif_runtime/policy.py`.

## Next slice
Extract `admission`, `permissions`, `approvals`, `trust`, `signatures`, `sandbox`,
and `provenance` contracts per ADR-0008 — each as its own schema once the
corresponding runtime module exists or is being built.
