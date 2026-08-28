# Mandare Fast-Path Routing Checklist

**Purpose:** Codify the Track A / Track B classification test so routing is a repeatable check, not a judgment call made fresh for each PR.

---

## Pipeline

```
                  Specification Review
                            │
            ┌───────────────┴───────────────┐
     Contract Change                 Existing Contract
            │                               │
     ADR Ratification                 Security / Defect Patch
      (Track B)                            (Track A)
            │                               │
    Structural Builder                Direct Merge
      (Track C)
```

---

**Normative Rule — Precedence:** This checklist governs routing precedence over PR labels, milestones, implementation plans, and reviewer expectations. If the checklist outcome conflicts with the track a PR was proposed under, the checklist takes precedence. "It was already planned as Track A" is not a valid basis for routing.

---

## The Routing Test

A PR is eligible for **Track A (fast-path, direct to Builder/merge)** only if it answers **NO** to both questions below. A single **YES** reroutes it to **Track B (Specification Review)** regardless of how the PR was originally scoped or described.

### Question 1 — Persisted schema, identity model, event contract, or replay-relevant behavior?
> Does this change modify any persisted schema, identity model, aggregate boundary, event/message contract, replay semantics, or the deterministic reconstruction of previously recorded Runs?

- Adding auth headers, fixing a comparison to be constant-time, closing an endpoint → **NO**
- Renaming a primary key, changing what an event carries, altering how a Run is reconstructed → **YES**

### Question 2 — Does the fix change any existing golden output?
> After applying the fix, does any current golden/fixture test produce a *different* output than before (not just pass/fail, but different content)?

**Golden output** includes: persisted records, emitted events, API payloads, replay artefacts, evidence bundles, governance logs, and any fixture treated as normative by the test suite.

- A fix that closes a vulnerability without altering any recorded expected output → **NO**
- A fix that happens to change what gets persisted, logged, or returned — even as a side effect of "just" fixing a bug → **YES**

**Rule:** If you can't answer Question 2 with certainty because the golden tests don't cover the affected path, treat that as a **YES** — **unknown = Track B until proven otherwise** — and route to Track B, or add fixture coverage before merging under Track A.

**Escalation clause:** If either question cannot be answered because the implementation is insufficiently understood, the reviewer shall stop routing and request clarification before classification. Guessing under time pressure is not an acceptable substitute for the checklist.

---

## Worked Examples

| Change | Q1 | Q2 | Route | Rationale |
|---|---|---|---|---|
| Add `ControlPlaneAuth` header check to `/v1/policy/evaluate` | No | No | **Track A** | Enforces existing intended access contract; no schema/replay impact |
| Replace `any()` generator comparison with constant-time compare | No | No | **Track A** | Pure security hardening, no behavior change for valid callers |
| Reverse `AuthorityEngine.resolve` default from `allowed=True` to `allowed=False` | No | No — ratified | **Track A** (PR #41) | Fixture check completed as part of Identity Spine Spec Review adoption: no golden test encoded the old default as intended behavior — it was the defect itself, not a documented contract |
| Escape template variables in `_freeze_intent()` | No (probably) | **Check** | **Track A, pending Q2 check** | If any existing template relies on unescaped interpolation for legitimate output, escaping changes that output — verify against fixtures before merging PR #41 |
| Add `SERIALIZABLE` isolation / advisory lock to `GovernanceLedger.append()` | No | No | **Track A** (standalone PR) | Enforces the existing append-only invariant; does not change the ledger schema or event contract. Scoped separately from the ledger's `run_id` re-key below. |
| `execution_id` → `run_id` re-key (GovernanceLedger, PostureManager, EvidenceBundle/Observation, Control-Plane API path params) | Yes | Yes | **Track B** | Changes aggregate boundaries, persistence schema, event contracts, and replay reconstruction — this is ADR-0010's subject matter directly. Sequenced on top of PR #31; dual-support alias for `execution_id` at the REST layer through v0.3.0. |
| Split `Decision` from `Execution` as separate entities | Yes | Yes | **Track B** | New aggregate structure — ADR-0012 |

---

## Process Notes

1. **The PR author's stated scope is a starting hypothesis, not the exit criterion.** Reviewers run this checklist during review regardless of how the PR description characterizes itself.
2. **Correctness does not determine routing. Contract impact determines routing.** A bug fix that changes persisted output, event shape, or replay reconstruction is a contract change wearing a bug-fix label — how urgently or obviously "correct" the fix is has no bearing on which track it belongs to.
3. **When Q2 is unknown**, the default is to treat it as a contract-change signal (Track B) rather than assume safety. Missing fixture coverage is a gap to close, not a reason to fast-path.
4. **Track A PRs still require review** — the checklist determines *routing*, not *whether review happens*.
5. **Logging is normative.** Every reviewed PR SHALL record: the final routing decision; the answers to Q1 and Q2; the reviewer; the date; and, if routed to Track B, the rationale. This is not optional documentation — it is the evidence trail that lets the fast-path itself be audited for scope creep over time.

---

## Invariant

> **Track A preserves existing contracts. Track B defines or modifies contracts. Track C implements previously ratified contracts.**

This single sentence is what the rest of this document exists to operationalize. If a proposed action doesn't fit cleanly into exactly one of these three, it hasn't been classified yet — return to the Routing Test.

---

## Appendix — Routing Record Template

Optional convenience template implementing the normative logging requirement (Process Note 5). Attach to the PR description or commit message; not part of the core checklist.

```
Routing Decision
----------------
Q1 (persisted schema / identity / event contract / replay-relevant?): Yes / No
Q2 (changes golden output?): Yes / No
Track: A / B
Reviewer:
Date:
Rationale (required if Track B):
```