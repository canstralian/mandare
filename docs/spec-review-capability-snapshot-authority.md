# Specification Review — Capability Snapshot Authority

**Repository:** canstralian/rif-runtime
**Governs:** the binding between an observed external capability catalog and an authorized run
**Status:** `Draft` — open for review. No implementation is authorized by this document.
**Document Lifecycle:** `Draft` (current) → `Approved Pending Governance Completion` → `Ratified` → `Superseded`
**Track:** B (Specification) — Builder work on capability binding is held until this document is approved
**Depends on:** `docs/spec-review-identity-spine-migration.md` (identity hierarchy), ADR-0008, ADR-0010, ADR-0012
**Source:** `docs/research/2026-08-16-research-baseline.md` §1, §5

---

## 1. Problem Statement

MCP `2026-07-28` removes protocol-level sessions and makes every request
self-describing and independently routable. Capability listings become cacheable
artifacts carrying `ttlMs` and `cacheScope`, with a deterministic order. Nothing
in the specification guarantees that a server's advertised capabilities — or the
implementation behind a stable capability name — remain fixed over time.

RIF's guarantee is that a decision is explainable and replayable. That guarantee
is only meaningful if we can say *what the decision was made against*. Today we
cannot, for any remotely-sourced capability.

This review exists to answer one question normatively:

> **What exact observation of the external capability environment becomes
> authoritative for an execution epoch, and what event semantics govern its
> replacement?**

### 1.1 Grounding in the current implementation

The gap is concrete, not hypothetical.

`PolicyEngine.evaluate()` (`src/rif_runtime/policy.py:40`) has this signature:

```text
evaluate(req, env_name, profile, posture, policy_rules) -> PolicyDecision
```

**No capability observation is an input.** A decision is computed entirely from
the request, local environment config, posture, and locally-stored rules. There
is presently no parameter through which a remote catalog observation *could*
bind, and `PolicyDecision` (`src/rif_runtime/schemas.py:29`) carries no field
referencing one — `matched_rule` identifies the rule, not the observed world the
rule was applied to.

Three existing pieces are the right shape and are the reason this is a small
contract question rather than a large one:

| Existing surface | What it already does | What it does not do |
| --- | --- | --- |
| `mcp/capabilities.py:contract_hash()` | Hashes the capability taxonomy and pins it into evidence "so a decision can be replayed against the exact capability contract that produced it" | Covers only the **static, locally-defined** taxonomy. A remote catalog is not hashed. |
| `resources/snapshot.py:ResourceSnapshot` | Immutable observation with `snapshot_id`, `generated_at`, `content_hash`, `metadata` | Is not bound to a `Run` or a `Decision`; nothing consumes it in the policy path. |
| `spec/mcp/SPEC.md` §8 | Requires a capability manifest at server **registration**, fixing "the T2 contract used for pinning" | Registration-time pinning is not run-time observation, and no rebinding semantics are defined. |

The docstring on `contract_hash()` already states this document's thesis. The
work is to generalize it from a local constant to an observed remote artifact.

### 1.2 Non-goals

This review does not design a discovery layer (see §8), does not authorize an MCP
gateway, does not define an evaluation subsystem, and does not modify the wire
protocol. It defines one binding and its replacement semantics.

---

## 2. Normative Invariant

**N-1 (Observation authority).** A run is authorized against a specific
capability *observation*, never against an assumption that a remote server is
stable.

**N-2 (No silent mutation).** An external catalog change MUST NOT alter the
authorization basis of an already-authorized unit of work. Authority may be
*withdrawn* by posture escalation or an explicit deny, but it is never silently
*redefined*.

**N-3 (Observation precedes authorization).** The ordering
`DISCOVER → SNAPSHOT → AUTHORIZE → EXECUTE → OBSERVE` is normative. No
authorization may consult a capability catalog that has not been reduced to an
immutable, content-addressed snapshot first.

These are binding. A change to any of them re-enters at Specification Review.

---

## 3. Normative Resolution — where the snapshot binds

This is the central question, and it does **not** require a new concept. It is
already answered by the ratified identity hierarchy in
`docs/spec-review-identity-spine-migration.md` §2:

```text
Project
 └── Session
      └── Run (Aggregate Root)
            ├── Decision
            ├── Execution*
            ├── Observation*
            ├── Verification*
            └── Evidence*
```

Three candidate bindings were considered.

| Option | Binding | Assessment |
| --- | --- | --- |
| **A** | `Run`-scoped: one snapshot per Run, immutable for the Run's life | Simple and safe, but forecloses legitimate long-running work that must pick up a changed catalog. A Run would have to be abandoned to re-observe. Rejected. |
| **B** | **`Decision`-scoped: each `Decision` carries exactly one `capability_snapshot_id`** | **Selected.** See below. |
| **C** | `Execution`-scoped: re-observe per mechanical attempt | Destroys authorization stability — a retry could silently execute against different capabilities than were authorized. Directly violates N-2. Rejected. |

### 3.1 Resolution

- [x] **Resolved — Normative (Decision-scoped binding).** A `capability_snapshot_id`
  binds to a `Decision`. Every `Decision` references exactly one capability
  snapshot. Every `Execution` inherits the snapshot of the `Decision` it carries
  out and MUST NOT re-observe.

The reason Option B is correct is that it makes "authorization epoch" a redundant
term. The identity spine already defines the exact object with those semantics:

> "Multiple Decisions exist only when the Run changes intent, authority, or
> planned parameters. Mechanical retries never create a new Decision."
> — identity spine review, §2

and

> "If a retry requires altered parameters or escalated authority, a new
> `Decision` must be evaluated (ADR-0012)."
> — identity spine review, §3

A capability catalog change *is* a change of authority. Therefore it produces a
new `Decision` by the already-ratified rule, with no new machinery.

**A new authorization epoch is a new `Decision`. RIF should not introduce
"epoch" as a distinct term.**

### 3.2 The brief's hard case, resolved

The originating research posed:

```text
Run
 ├── capability snapshot A
 ├── tool call 1
 ├── external catalog changes
 ├── tool call 2
 └── policy decision
```

**Resolution.** Tool call 2 remains governed by snapshot A. Snapshot A is bound
to the `Decision` under which both calls are `Execution`s, and N-2 forbids the
external change from redefining it. If the runtime *observes* the change and that
change is material (§4.2), it MUST evaluate a new `Decision` before tool call 2
proceeds; tool call 2 then executes under snapshot B, and the Run carries both
Decisions in order. If the change is not observed, tool call 2 proceeds under A —
correctly, because A is what was authorized and what the audit trail claims.

The Run is never retroactively rewritten. Both outcomes are explainable.

---

## 4. Snapshot lifetime and replacement

### 4.1 `ttlMs` is a re-observation trigger, not an invalidation

- [x] **Resolved — Normative.** Expiry of a snapshot's `ttlMs` MUST NOT
  invalidate an in-flight `Decision`. It marks the snapshot **stale for new
  authorization**, requiring re-observation before the *next* `Decision`.

Rationale: `ttlMs` is freshness metadata from a source with no stability
obligation. Treating expiry as invalidation would let a remote server abort a
governed run by letting a cache entry lapse — handing availability control to the
least trusted party in the circuit. Treating it as a re-observation trigger keeps
authority local.

### 4.2 Re-observation outcomes

Re-observation produces a snapshot id. Two cases:

- **Identical `capability_snapshot_id`** — the observed world is unchanged. The
  existing `Decision` continues. No new `Decision`, no new evidence beyond the
  re-observation record itself.
- **Differing `capability_snapshot_id`** — the observed world changed materially.
  A new `Decision` MUST be evaluated before further `Execution`s (§3.1).

This makes snapshot-id stability load-bearing, which raises §4.3.

### 4.3 Canonicalization MUST NOT depend on server-supplied ordering

MCP `2026-07-28` specifies deterministic list ordering. That is a *specification
requirement on servers*, not a property RIF can verify, and RIF's threat model
already treats server-supplied metadata as untrusted.

- [x] **Resolved — Normative.** Snapshot canonicalization MUST be order-independent
  on the RIF side: entries are sorted by RIF before hashing, using
  **RFC8785-JCS** canonicalization, consistent with the existing `integrity` block
  in `spec/capability/capability_manifest.schema.json` and with the sorted-set
  hashing already used by `mcp/capabilities.py:contract_hash()`.

If RIF hashed the server's ordering directly, a server could force spurious
re-authorizations — or, worse, a benign reordering could mask a material change
by producing churn that operators learn to ignore.

### 4.4 `cacheScope` governs snapshot sharing

- [ ] **Open (OD-C1).** `cacheScope` is a governance signal, not merely a caching
  hint: it bears on whether one observation may be reused as the authorization
  basis for a different actor, environment, or identity. Proposed default —
  **snapshots are never shared across environment profiles**, and a `cacheScope`
  narrower than the reuse RIF intends MUST force re-observation. Needs a concrete
  mapping from the spec's `cacheScope` values to RIF's environment/identity model
  before ratification.

### 4.5 Absent observation

- [x] **Resolved — Normative.** Where no capability observation exists — a server
  that was never discovered, or discovery that failed — the snapshot reference is
  the **explicit absence sentinel**, not a null that reads as "unknown". A
  decision made without a capability observation must be visibly distinguishable
  in the audit trail from one made against an observed empty catalog. Deny-by-
  default still governs the decision itself; this rule is about the evidence being
  honest.

---

## 5. Execution evidence and evaluation evidence are separate

- [x] **Resolved — Normative.** Evidence produced by the runtime (`ExecutionEvidence`)
  and evidence produced by any assessor of the runtime (`EvaluationEvidence`) are
  distinct record types. `EvaluationEvidence` MUST NOT be an input to replay, and
  MUST NOT participate in any policy decision.

```text
ExecutionEvidence          EvaluationEvidence
├── path_hash              ├── evaluator_id
├── policy_receipts        ├── evaluator_model
├── effect_receipts        ├── evaluator_version
└── replay_result          ├── rubric_hash
                           ├── input_evidence_hash
                           └── score
```

A deterministic trajectory does not imply a deterministic score: any LLM judge is
a second probabilistic subsystem. If a score could re-enter execution, replay
would stop being a function of recorded history.

This section defines **vocabulary and a prohibition**. It does not authorize an
evaluation subsystem, and RIF has none. Its purpose is to make a future
evaluation layer unable to contaminate execution replay by construction, and to
give reviewers a citable line when one is proposed.

---

## 6. Replay is not recovery

- [x] **Resolved — Normative.** `Replay` reconstructs history. `Recovery`
  continues execution. They MUST NOT share an API surface, and replay MUST remain
  free of side effects.

```text
Replay   = reconstruct history      (read-only, deterministic, no effects)
Recovery = continue execution       (may produce new Executions and new effects)
```

Current state: `src/rif_runtime/replay.py` rebuilds graph and posture from
`decisions.jsonl` and is correctly read-only. Nothing presently documents that
this is a *requirement* rather than an implementation detail, which is exactly
how such boundaries erode — a future "resume from replay" convenience would look
like a small feature and would silently make history mutable.

Interaction with §3: recovery resumes under the `Decision` it left off at, and
therefore under that Decision's snapshot. Recovery MUST NOT re-observe
capabilities implicitly; if the catalog has changed materially, recovery
surfaces a new `Decision` rather than quietly continuing under a new world.

---

## 7. Conformance requirements

A conforming implementation of this contract MUST:

1. Reduce every consulted capability catalog to an immutable, content-addressed
   snapshot before authorization (N-3).
2. Bind exactly one `capability_snapshot_id` to each `Decision` (§3.1).
3. Inherit, never re-observe, the snapshot for each `Execution` under a
   `Decision` (§3.1).
4. Canonicalize snapshots order-independently via RFC8785-JCS (§4.3).
5. Treat `ttlMs` expiry as a re-observation trigger, never as invalidation of an
   in-flight `Decision` (§4.1).
6. Evaluate a new `Decision` when re-observation yields a differing snapshot id
   (§4.2).
7. Record absent observation explicitly rather than as a null (§4.5).
8. Keep `EvaluationEvidence` out of replay and out of policy (§5).
9. Keep replay side-effect free and API-distinct from recovery (§6).

---

## 8. Explicitly out of scope

| Item | Why |
| --- | --- |
| Discovery Evidence schema | ARD is v0.9 with no measured catalog adoption outside two reference implementations (baseline §4). The shape is recorded; the slice is not justified. |
| MCP gateway interception | Viable insertion point (baseline §2), but blocked on this contract. Also: W3C Trace Context is **not** guaranteed by MCP `2026-07-28` — a gateway must originate correlation identifiers itself. |
| Evaluation subsystem | §5 defines vocabulary and a prohibition only. |
| Benchmark decomposition | Vocabulary only (baseline §3). |
| Meta-Harness | Rejected for the runtime (baseline §8). |
| Execution-environment evidence (`model_id`, `runtime_revision`, …) | Deferred; evidence, not policy (baseline §6). |

---

## 9. Open decisions

- **OD-C1.** `cacheScope` → RIF environment/identity mapping (§4.4).
- **OD-C2.** Snapshot scope granularity: one snapshot per MCP server, or one
  merged snapshot across all servers consulted by a `Decision`? Per-server is
  simpler to invalidate; merged is simpler to bind to a single
  `capability_snapshot_id`. Proposed: merged snapshot whose canonical form is the
  sorted set of per-server content hashes — giving one id per Decision while
  keeping per-server invalidation tractable.
- **OD-C3.** Snapshot retention and storage. Snapshots are needed for replay, so
  retention must be ≥ audit retention. Proposed: `JsonlStore`, keyed by
  `capability_snapshot_id`, deduplicated (identical observations recur often).
- **OD-C4.** Relationship to `spec/mcp/SPEC.md` §8 registration-time pinning. Does
  the registration manifest become the first snapshot, or is registration a
  separate T2 admission artifact that snapshots reference? Proposed: separate —
  registration admits a server, snapshots observe it, and conflating them would
  make re-observation imply re-admission.
- **OD-C5.** Whether `PolicyDecision` gains a `capability_snapshot_id` field
  directly, or whether the reference lives on `Decision` in the identity-spine
  model with `PolicyDecision` remaining the evaluation result. Depends on
  sequencing against the identity-spine migration; must not be resolved
  unilaterally at Builder stage.

---

## 10. Review checklist

- [ ] Confirm Option B (Decision-scoped binding) against ADR-0012.
- [ ] Resolve OD-C1 through OD-C5.
- [ ] Confirm sequencing against the identity-spine migration — this contract
      assumes `Decision` exists as a first-class entity.
- [ ] Add OD-6 cross-reference in `spec/mcp/SPEC.md` §13. *(done — see that file)*
- [ ] Decide whether §6 (replay ≠ recovery) should be extracted into the
      `spec/replay/` contract now, since it is stated normatively here and
      `spec/replay/` is still a placeholder.
- [ ] Sign-off before any Builder work begins.
