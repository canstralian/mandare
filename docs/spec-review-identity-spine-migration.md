# Specification Review — Identity Spine Migration

**Repository:** canstralian/rif-runtime
**Governs:** ADR-0010 (Run as sole aggregate root)
**Status:** Approved Pending Governance Completion (architecture review score: 9.95/10 — no remaining architectural unknowns; remaining items are implementation-governance tasks, not design decisions)
**Document Lifecycle:** `Draft` → `Approved Pending Governance Completion` (current) → `Ratified` (upon completion of Section 11's governance checklist and sign-off) → `Superseded` (only upon an explicit future ADR that replaces this document). From `Ratified` onward, any proposal changing the aggregate root, identity hierarchy, replay model, correlation semantics, or the Architectural Invariants (Section 13) is an amendment to this specification, not an implementation detail — it re-enters at Specification Review (Track B), not Builder.
**Track:** B (Specification) — Builder work on this domain is held until this document is approved
**Related findings:** RIF Architectural Conformance Analysis; ADR-0008, ADR-0010, ADR-0012, ADR-0015

---

## 1. Problem Statement

The Phase 4 implementation uses `execution_id` as the top-level lifecycle spine. This conflicts with ADR-0010, which mandates `Run` as the sole aggregate root. Conflating the macro run lifecycle with individual execution attempts prevents safe modeling of retries, rollbacks, and sandboxing.

A secondary, coupled defect: Decisions (intent and policy evaluation) are not strictly separated from Executions (mechanical attempts), violating ADR-0012.

Both defects trace back to the same unresolved question, which this review exists to answer normatively:

> **What is the immutable identity of a "thing" in RIF?**

---

## 2. Normative Identity Hierarchy

This hierarchy is the anchor for every ADR going forward. Any future architectural decision that implies a different shape must be reconciled against this section, not silently diverge from it.

```
Project
 └── Session
      └── Run (Aggregate Root)
            ├── Decision
            ├── Execution*
            ├── Observation*
            ├── Verification*
            └── Evidence*
```
`*` denotes a one-to-many relationship.

**Normative — Aggregate Ownership:** No entity beneath `Run` may exist independently of a `Run`. `Decision`, `Execution`, `Observation`, `Verification`, and `Evidence` are lifecycle-scoped child entities and derive their existence from their parent `Run`. This forecloses any future treatment of `Execution` (or any other child entity) as a reusable or independently-addressable aggregate.

**Definitions:**

| Entity | Cardinality under Run | Definition |
|---|---|---|
| `Run` | 1 (is the root) | The macro lifecycle unit — the aggregate root. Owns identity for everything beneath it. |
| `Decision` | One or more, ordered | Intent and policy evaluation — *what should happen*, prior to any mechanical attempt. Multiple Decisions exist only when the Run changes intent, authority, or planned parameters. Mechanical retries never create a new Decision. |
| `Execution` | many | A single mechanical attempt to carry out a Decision. Retries and rollbacks are modeled as multiple Executions under one Run. |
| `Observation` | many | Raw, directly-observed data produced during an Execution. |
| `Verification` | many | Assessment of whether an Execution's outcome satisfied its Decision. |
| `Evidence` | many | The governance-facing record derived from Observation/Verification, used for audit and replay. |

**Resolved:** `Session` is **optional**. `session_id` is a nullable FK on `Run`. Interactive multi-turn agent workflows operate within a Session context; background jobs, cron evaluations, and direct CLI runs execute as standalone `Run` aggregates without a session parent. This avoids forcing dummy sessions while preserving clean relational boundaries when a session does exist. *(Resolved — see Section 10.)*

### Identity Invariants

- `run_id` never changes.
- `decision_id` never changes once issued.
- `execution_id` identifies one mechanical attempt only — it is never reused or reassigned.
- Evidence is append-only.
- Replay never mutates identifiers.

These invariants are binding on all future migrations. Any migration or schema change that would violate one of these lines must return to this Specification Review for amendment before proceeding — it cannot be resolved unilaterally at the Builder stage.

---

## 3. Aggregate Boundaries

- [x] **Resolved (Section 2, Normative — Aggregate Ownership):** `Run` is the sole transactional consistency boundary — no cross-Run invariants are enforced at the domain layer; no child entity may exist independently of a `Run`.
- [x] **Resolved (Section 2):** `Decision` and `Execution` are separate entities, not fields on a shared record (ADR-0012 compliance) — codified in the Decision cardinality definition and retry-semantics resolution below.
- [x] **Resolved:** `Observation`, `Verification`, and `Evidence` derive their identity from the owning `Run` through their parent `Execution` and/or `Decision`. They are never independently addressable aggregates.
- [x] **Resolved:** retries of an identical action share the same `Decision`. A `Decision` captures authorization, policy evaluation, and intended parameters; a mechanical failure (e.g. HTTP 503, network drop) does not invalidate the original decision — a retry spawns a new `Execution` referencing the existing `decision_id`. If a retry requires altered parameters or escalated authority, a new `Decision` must be evaluated (ADR-0012).

---

## 4. Persistence Schema Implications

- [ ] All tables currently keyed on `execution_id` must be identified and re-keyed to `run_id` (plus a subordinate `execution_id` where Execution-level granularity is still needed).
- [ ] Foreign key constraints and cascade rules must be redefined around `Run` as root.
- [x] **Resolved:** the `run_id` re-key sequences **on top of PR #31**, not in parallel. PR #31 establishes the baseline Supabase schema and `project_id` RLS policies; the re-key lands as a subsequent migration once that baseline is settled.
- [x] **Resolved:** historical rows receive a **synthetic `run_id`**, generated deterministically per legacy `execution_id`. Original `execution_id` values are preserved (not overwritten). No data is discarded. Replay remains available for pre-migration runs under the synthetic `run_id`. Legacy-freeze is out of scope unless a specific historical run is found where replay genuinely cannot be reconstructed under this scheme — such cases are handled as documented exceptions, not the default path.

---

## 5. Event Contract Implications

**Normative:** `run_id` is the canonical correlation identifier for all runtime events. `execution_id` may appear only as metadata describing an individual execution attempt — it must never be used as a correlation key for joining or grouping events.

- [ ] Enumerate every event type currently emitting `execution_id` as its correlation key.
- [ ] Define the new event schema versions (per the Run Observation / Execution Record / Evaluation Record versioning convention already in use).
- [ ] Confirm downstream consumers (evidence ledger, replay engine, `adhd_reasoning` capability if applicable) are inventoried before the cutover — this is a breaking change to any consumer keyed on the old identity.

---

## 6. Replay Semantics Implications

Replay reconstructs the full chain — `Run → Decision(s) → Execution(s) → Observation(s) → Verification(s) → Evidence` — not simply Executions. This reinforces the Decision/Execution separation mandated by ADR-0012: reconstructing Executions alone, without their governing Decisions, is not a valid replay.

- [ ] Replay is authoritative (per the Replay gate) — confirm the re-key preserves deterministic replay for all *existing* recorded runs, or explicitly scope legacy runs as non-replayable under the new schema.
- [ ] Confirm replay boundary is unaffected by the Decision/Execution split — replay must still reconstruct a full Run from its child Executions in original order.

---

## 7. Evidence Lineage & API Contract Implications

- [ ] Confirm every Evidence record retains an unbroken chain back to its `run_id`, not `execution_id`.
- [x] **Resolved:** dual-support window is a single minor-release deprecation, `v0.2.x → v0.3.0`, scoped to the REST/control-plane layer only. Persistence and internal domain layers cut over to `run_id` immediately. **v0.2.x responses always emit `run_id`; the `execution_id` alias is accepted only on input** (request path/query params), never emitted in output — this prevents clients from forming a new dependency on the deprecated field via response payloads. Input alias support (with an HTTP `Deprecation` header) is removed at `v0.3.0`.
- [ ] Confirm no external consumer contract (if any exists outside this repo) is silently broken by the rename.

---

## 8. Compatibility Matrix

| Component | Current keys on `execution_id` | Action required | Route classification |
|---|---|---|---|
| GovernanceLedger | Yes | Re-key `execution_id` → `run_id`. Apply `SERIALIZABLE` isolation / advisory lock. | Split: lock fix is **Track A**; re-key is **Track B** |
| PostureManager | Yes — posture transitions recorded in `data/posture_history.jsonl` carry only `{"old_posture", "new_posture"}` fields today; no `run_id` or `execution_id` is written at the point of escalation (`runtime.py:77-79`). The escalation epoch is therefore correlated to an `execution_id` only implicitly, via temporal proximity to the surrounding decision row in `decisions.jsonl`. The `ReflexiveLoop` derives denial counts from a 60-minute rolling `TelemetryStore` window — it never persists a correlation key. | Re-key posture transition records to include `run_id` (and optionally the triggering `decision_id`) at the time of write (`runtime.py:record_decision`). Update `ReplayEngine` to consume `run_id` when replaying posture history. Hardcoded thresholds (3 / 10 / 20 denials) in `PostureManager.next_posture` are out of scope for the re-key but should move to config as a coupled Track B cleanup. | **Track B** |
| AuthorityEngine / PolicyEngine | No | Reverse default-allow to fail-closed (`allowed=False`). | **Track A** (PR #41) |
| EvidenceBundle / Observation | Yes — `EvidenceEvent` (`mcp/metasploit.py:154-166`) records a self-generated `decision_id` (a fresh `uuid4()` independent of the `PolicyDecision.timestamp`, not correlated to a `run_id`). Fields: `decision_id`, `intent_hash`, `tool`, `requested_capability`, `policy_decision`, `scope_id`, `contract_hash`, `matched_rule`, `timestamp`, `signature`. Appended to `data/metasploit_evidence.jsonl` (`runtime.py:112`). Each `EvidenceEvent` maps 1-to-1 to a `GovernanceOutcome`/`PolicyDecision` but carries no `run_id`, `execution_id`, or FK to the parent `decisions.jsonl` row. The general-purpose `PolicyDecision` persisted to `decisions.jsonl` has the same gap — no `run_id` field in `schemas.PolicyDecision`. | Add `run_id` field to `PolicyDecision` schema (and therefore to every row in `decisions.jsonl`). Add a matching `run_id` to `EvidenceEvent`, derived from the owning `Run`. Unroll coarse `EvidenceBundle` semantics into per-`Execution` `Observation` rows referencing the parent `run_id` per the normative hierarchy (Section 2). Update `MetasploitGovernor._sign_evidence` to accept and embed `run_id`; update `RIFRuntime.evaluate_metasploit` to pass it through. | **Track B** |
| Control-Plane API | Yes | Implement `ControlPlaneAuth` header check. Update path params to `run_id` with deprecation alias per Section 7. | Split: auth is **Track A** (PR #41); re-key is **Track B** |

This table is the primary deliverable evidence for the Traceability Report. The two Track A items above (GovernanceLedger lock, control-plane auth) execute immediately and independently of this review's ratification — see Section 14.

---

## 9. Migration Strategy

- [x] **Resolved (per Section 4):** this review does not block PR #31 — the `run_id` re-key sequences on top of PR #31 as a subsequent migration, and PR #31 proceeds independently.
- [x] **Resolved:** rollback refers to migration execution only — it restores the pre-migration schema and data state. It does **not** revoke the architectural decision establishing `Run` as the aggregate root (ADR-0010 itself is not subject to migration rollback; a failed migration is retried or re-planned, not treated as grounds to reopen the ratified specification).
- [ ] Test strategy: golden-test contract updates required (RIF-COMP-001) — enumerate which fixtures need regeneration vs. which can be left as frozen legacy cases.

---

## 10. Open Questions — Resolved

1. **Session mandatory or optional?** → Optional. `session_id` is a nullable FK on `Run`. (Section 2)
2. **Do retries share a Decision?** → Yes, for identical actions; a new `Decision` is required only if parameters or authority change. (Section 3)
3. **Ledger re-key vs. PR #31 sequencing?** → Sequenced on top of PR #31, not parallel. (Section 4, Section 9)
4. **Dual-support window for `execution_id`?** → Single minor-release deprecation, `v0.2.x → v0.3.0`, REST layer only; internal layers cut over immediately. (Section 7)

All four questions carried a resolution and rationale as of this revision. No open questions remain blocking ratification.

---

## 11. Approval Criteria

**Architecture review verdict:** Approved Pending Governance Completion (score 9.95/10). No architectural unknowns remain. All prior required amendments are incorporated (Sections 2, 3, 4, 5, 6, 7, 9, 13). Remaining items below are implementation-governance tasks — consumer inventory, fixture regeneration, replay verification, ADR cross-reference, sign-off — not design decisions, and do not require reopening the architecture.

This document is ratified when:
- [x] All Open Questions (Section 10) have documented answers.
- [x] Required amendments from architecture review are incorporated.
- [x] All architectural lineage, sequencing, and rollback-scope items in Sections 3, 4, and 9 are resolved.
- [ ] Section 5: event-type enumeration and downstream-consumer inventory completed.
- [ ] Section 6: replay preservation confirmed for all existing recorded runs (or legacy runs explicitly scoped as non-replayable).
- [ ] Section 7: confirmed no external consumer contract outside this repo is silently broken by the rename.
- [x] Section 8: PostureManager and EvidenceBundle/Observation audit detail populated in the compatibility matrix.
- [ ] Section 9: golden-test fixture enumeration (regenerate vs. frozen-legacy) completed.
- [ ] ADR-0010 is updated to reference this document as its implementation authority.
- [ ] Specification Governor (or acting equivalent) signs off.
- [ ] Builder is released for Track C (R0–R9 resumption) only after this line is checked.

**Sign-off:**

| Role | Name | Date | Status |
|---|---|---|---|
| Specification Governor | | | Pending |
| Runtime Architect | | | Pending |

---

## 13. Architectural Invariants (Traceability)

These invariants are mechanically verifiable by reviewers and, where feasible, should be enforced by tests or database constraints rather than convention alone.

- Every runtime event correlates to exactly one `run_id`.
- Every `Run` has ≥ 1 `Decision`.
- Every `Execution` references exactly one `Decision`.
- Every `Execution` belongs to exactly one `Run`.
- Every `Observation` references one `Execution`.
- Every `Verification` references one `Execution`.
- Every `Evidence` record traces to one `Run`.
- No child entity may migrate between Runs.
- Replay SHALL use only persisted identifiers (synthetic `run_id` generation per Section 4 applies only to one-time historical backfill, not to live replay).

---

## 14. Next Actions

1. **Adopt governance artifact** — the companion `RIF Fast-Path Routing Checklist` is adopted into repository review guidelines and applied to all future Track A/B classification decisions.
2. **Execute Track A now, independent of this review's ratification:**
   - Complete review and merge **PR #41** (control-plane auth, fail-closed reversal, constant-time comparison, template-injection fix).
   - Complete review and merge a **standalone `GovernanceLedger` advisory-lock PR** (`SERIALIZABLE` isolation / advisory lock) — scoped separately from the ledger re-key, which remains Track B.
3. **Ratify this Specification Review** with the resolutions in Section 10 to unblock Track C (R0–R9 Builder work on the identity spine).