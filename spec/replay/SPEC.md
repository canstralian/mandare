# RIF Runtime Deterministic Replay Engine v1.0

**Status:** Frozen design (Track B contract).  
**Depends on:** [`spec/events/SPEC.md`](../events/SPEC.md) (`rif.runtime.event/v1`).  
**Implements direction from:** ADR-0002 (audit events as canonical replay source).  
**Supersedes for v1.0 design:** ad-hoc `ReplayEngine.recover()` over bare `PolicyDecision` JSONL (legacy adapter only).

## Assumptions

1. Event log is **append-only JSONL**, one `rif.runtime.event/v1` envelope per line, single writer per `run_id`.
2. **Side effects** are represented only as capability/execution events (`capability.*`, `execution.*`). Pure replay never calls external systems.
3. **Evidence artifacts** are content-addressed (`evidence_refs.kind = content_sha256` or `evidence.recorded.payload.content_sha256`).
4. Causal order is `(run_id, sequence)`. `recorded_at` is observational and ignored for folding.
5. Governance outcomes in the log are **authoritative** via `governance.evaluated.payload.posture_after` (and related fields). Replay does not re-run a wall-clock denial window.

## Goals

| Goal | Mode |
| --- | --- |
| Reconstruct runtime state at any event index | Pure / time-travel |
| Recompute and check integrity without re-executing capabilities | Verify-only |
| Detect where a candidate log or re-fold diverges | Divergence detection |
| Validate hash chain + derived `event_id` | Hash verification |
| Support operator debugging (“state after sequence N”) | Time-travel |

## Non-goals

- Re-invoking nondeterministic models/tools and expecting bit-identical outputs (verify compares **hashes**, not live re-execution unless a capability is marked pure).
- Multi-run global merge without a sequence allocator.
- Migrating legacy `decisions.jsonl` (separate adapter; out of scope of this algorithm).

---

## 1. State machine definition

### Run lifecycle (high level)

```text
                  intent.received
   [Absent] ----------------------> [Accepted]
                                       |
                                  mode.selected
                                       v
                                  [ModeBound]
                                       |
                    memory.retrieved / context.built
                                       v
                                  [ContextReady]
                                       |
                             governance.evaluated
                          /            |            \
                      deny           allow         review
                        |              |              |
                        v              v              v
                   [Denied]      [Authorized]    [ReviewHold]
                                       |
                            budget.debited*
                                       |
                            capability.requested
                                       |
                      +----------------+----------------+
                      |                                 |
              capability.granted                capability.denied
                      |                                 |
                      v                                 v
                [Granted]                          [Denied]
                      |
              execution.started
                      |
                      v
                [Executing]
                 /        \
   execution.completed   execution.failed
           |                    |
           v                    v
      [Succeeded]           [Failed]
           \                    /
            evidence.recorded*
                     |
                     v
              [Terminal-ish]
                     |
              replay.completed (meta; may append later)
```

`*` = optional / may repeat. A run may end at `Denied` without execution.

### Fold phases (engine-internal)

The engine itself is a fold with explicit phases:

```text
  LOAD -> VALIDATE_ENVELOPE -> VERIFY_HASH -> APPLY_REDUCER -> (optional COMPARE)
                                                     |
                                                     +-> CHECKPOINT (if index hit)
```

| Phase | Pure | Verify-only | Notes |
| --- | --- | --- | --- |
| LOAD | read JSONL | read JSONL | Fail on decode |
| VALIDATE_ENVELOPE | schema + causality | same | sequence, causation |
| VERIFY_HASH | optional (config) | **required** | chain + event_id |
| APPLY_REDUCER | **yes** | no (or dry apply for compare) | mutate `ReplayState` |
| COMPARE | N/A | vs expected digest/state | divergence |
| CHECKPOINT | on `--at` / every N | on mismatch | time-travel |

### Terminal status enum

```text
absent | accepted | mode_bound | context_ready | authorized | denied
| review_hold | granted | executing | succeeded | failed | aborted
```

Derived from the highest-sequence event applied, not from wall clock.

---

## 2. Replay algorithm

### Inputs

- `log`: ordered events for one `run_id` (or filter by `run_id`)
- `mode`: `pure` | `verify` | `time_travel`
- `at_sequence`: optional upper bound (inclusive); default = last event
- `evidence_store`: map `sha256 -> bytes` (or existence oracle)
- `expected` (verify): optional prior `ReplayReport` or head hashes

### Pure replay (reconstruct)

1. `state ← empty_state(run_id)`
2. `prev_hash ← GENESIS` (`0` × 64)
3. For each event `e` in log order with `e.sequence ≤ at_sequence`:
   1. Assert `e.run_id == run_id`
   2. Assert `e.sequence == state.sequence + 1` (strict monotonic, no gaps)
   3. Validate causation (root or prior id)
   4. Optionally verify hashes (recommended on)
   5. `state ← reduce(state, e)`
   6. `prev_hash ← e.integrity.event_sha256`
4. Return `ReplaySnapshot(state, head_hash=prev_hash, index=at_sequence)`

**Pure mode never:** opens network, invokes capabilities, reads wall clock for decisions, or mutates the authoritative log.

### Verify-only mode

For each event (up to `at_sequence`):

1. Recompute canonical preimage and `event_sha256` / `event_id` per events SPEC §5.
2. Check `integrity.previous_event_sha256 == prev_hash`.
3. If `result_hash` present: ensure it matches canonical hash of `payload.result`.
4. For each `content_sha256` evidence ref: assert artifact exists (and optional byte digest match).
5. Do **not** require capability re-execution.
6. Optionally fold state in parallel and compare `state_digest(state)` to an expected checkpoint.

Emit `Divergence` on first failure; continue-only if `fail_fast=false`.

### Divergence detection

Compare at event `e`:

| Layer | Expected | Actual | On mismatch |
| --- | --- | --- | --- |
| Envelope hash | logged `event_sha256` | recomputed | `HASH_MISMATCH` |
| Event id | logged `event_id` | `evt_`+recomputed | `ID_MISMATCH` |
| Chain link | logged `previous_event_sha256` | fold `prev_hash` | `CHAIN_BREAK` |
| State digest | checkpoint / golden | `state_digest(state)` after reduce | `STATE_DIVERGENCE` |
| Evidence | ref id | store presence/digest | `EVIDENCE_MISSING` |
| Capability effect | logged execution result hash | (verify-only) stored hash only | N/A unless re-exec mode |

First mismatch records `divergence_sequence`, `divergence_event_id`, `reason_code`, and optional before/after state digests.

### Time-travel debugging

- `snapshot(at_sequence=N)` → full `ReplayState` after applying events `1..N`.
- `diff(N, M)` → structural diff of two snapshots (posture, budget, grants, graph edges, status).
- Optional checkpoints every K events: store `state_digest` + key fields to speed bisect.
- Bisect: find least `N` where `state_digest` ≠ golden or verify fails.

---

## 3. Pseudocode

```text
GENESIS = "0" * 64

function replay(log, mode, at_sequence=∞, evidence_store={}, expected=None):
    events = sort_and_filter(log)  # by sequence ascending
    state = EmptyReplayState()
    prev_hash = GENESIS
    report = ReplayReport(mode=mode)

    for e in events:
        if e.sequence > at_sequence:
            break

        err = validate_envelope(e, state)
        if err: return fail(report, e, err)

        if mode in {verify, pure} and hash_checks_enabled:
            err = verify_event_hash(e, prev_hash)
            if err: return fail(report, e, err)

        if mode == verify:
            err = verify_evidence_refs(e, evidence_store)
            if err: return fail(report, e, err)

        # Apply reducer in pure and time_travel; in verify apply when
        # state checkpoints are requested.
        if mode != verify or expected is not None:
            state = reduce(state, e)
            if expected and expected.digests[e.sequence] != state_digest(state):
                return fail(report, e, STATE_DIVERGENCE)

        prev_hash = e.integrity.event_sha256
        report.events_applied += 1

    report.snapshot = Snapshot(state, prev_hash, min(at_sequence, last_seq))
    report.ok = true
    return report


function reduce(state, e):
    state.sequence = e.sequence
    state.last_event_id = e.event_id
    state.actors.add(e.actor)

    switch e.type:
        case intent.received:
            state.status = accepted
            state.environment = e.payload.environment
            state.intent_hash = e.payload.intent_hash

        case mode.selected:
            state.status = mode_bound
            state.mode = e.payload.mode
            state.posture = e.payload.posture

        case memory.retrieved:
            state.memory_item_hashes = e.payload.item_hashes

        case context.built:
            state.status = context_ready
            state.context_hash = e.payload.context_hash

        case governance.evaluated:
            state.posture = e.payload.posture_after
            state.last_decision = e.payload.decision
            state.graph.add_edge(e.payload.request, e.payload.decision)
            state.denial_count += 1 if decision == deny else 0
            state.status = authorized | denied | review_hold

        case budget.debited:
            state.budget = e.budget   # envelope snapshot is authoritative

        case capability.requested:
            state.pending_capability = e.capability

        case capability.granted:
            state.status = granted
            state.active_grant = e.payload.grant_token_hash

        case capability.denied:
            state.status = denied
            state.active_grant = null

        case execution.started:
            state.status = executing
            state.execution_id = e.payload.execution_id

        case execution.completed:
            state.status = succeeded
            state.last_result_hash = e.result_hash

        case execution.failed:
            state.status = failed
            state.last_error_code = e.payload.error_code

        case evidence.recorded:
            state.evidence_index.add(e.payload.content_sha256)

        case replay.completed:
            # Meta-event: do not change governed status; record verify outcome
            state.last_replay_matched = e.payload.matched

    return state


function verify_event_hash(e, prev_hash):
    if e.integrity.previous_event_sha256 != prev_hash:
        return CHAIN_BREAK
    preimage = canonical_preimage(e)  # excludes event_id + event_sha256
    digest = sha256_hex(preimage)
    if digest != e.integrity.event_sha256: return HASH_MISMATCH
    if e.event_id != "evt_" + digest: return ID_MISMATCH
    if e.result_hash is set:
        if e.result_hash != sha256_hex(canonical(e.payload.result)):
            return RESULT_HASH_MISMATCH
    return OK
```

---

## 4. Data structures

```text
ReplayState:
  run_id: RunId
  sequence: int                 # last applied
  last_event_id: EventId | null
  status: RunStatus
  environment: str | null
  mode: str | null
  posture: Posture              # from governance/mode events
  intent_hash: Sha256 | null
  context_hash: Sha256 | null
  memory_item_hashes: [Sha256]
  denial_count: int             # count of deny decisions applied (for metrics)
  last_decision: Decision | null
  budget: BudgetSnapshot | null
  pending_capability: CapabilityId | null
  active_grant: Sha256 | null
  execution_id: str | null
  last_result_hash: Sha256 | null
  last_error_code: str | null
  evidence_index: set[Sha256]
  graph: GovernanceGraphView    # actor/action/target/decision edges
  actors: set[Actor]
  last_replay_matched: bool | null

Snapshot:
  state: ReplayState
  head_hash: Sha256             # last event_sha256 or GENESIS
  at_sequence: int
  state_digest: Sha256          # sha256(canonical(ReplayState public fields))

Divergence:
  reason_code: enum
  sequence: int
  event_id: EventId
  expected: str | null
  actual: str | null

ReplayReport:
  ok: bool
  mode: pure | verify | time_travel
  events_applied: int
  snapshot: Snapshot | null
  divergence: Divergence | null
  warnings: [str]

EvidenceStore:
  # content-addressed
  has(sha256) -> bool
  get(sha256) -> bytes | null
```

### `state_digest`

Canonical JSON over a **stable public subset** of `ReplayState` (exclude any ephemeral debugger fields). Used for golden tests and divergence.

### Persistence recommendation

```text
data/events/<run_id>.jsonl
data/evidence/<sha256>          # raw bytes
data/replay/<run_id>/checkpoints.jsonl   # optional: {sequence, state_digest, head_hash}
```

---

## 5. Complexity analysis

Let `N` = events in the run up to `at_sequence`, `E` = evidence refs per event (bounded, ≤ 64), `S` = size of canonical event bytes, `G` = graph edges ≤ `N`.

| Operation | Time | Space |
| --- | --- | --- |
| Pure replay to end | `O(N · S)` hash optional + `O(N)` reduce | `O(N)` graph worst case, typically `O(G)` |
| Verify-only (hashes + evidence existence) | `O(N · S + N · E)` | `O(1)` extra besides report |
| Time-travel snapshot at `K` | `O(K · S)` from scratch | one `ReplayState` |
| Bisect with checkpoints every `C` | `O((N/C) + C · S)` with stored digests | `O(N/C)` checkpoint digests |
| Diff two snapshots | `O(|state|)` | temp |

**I/O:** Single sequential read of JSONL is optimal for append-only logs. Random access by sequence requires either scan or an offset index (`O(N)` build once).

**Bottleneck:** Canonicalization + SHA-256 per event in verify mode. Acceptable for governance-scale `N` (thousands–millions); for very large `N`, checkpoint digests avoid full re-fold during bisect.

---

## 6. Failure modes

| Code | Cause | Recovery |
| --- | --- | --- |
| `DECODE_ERROR` | Invalid JSONL line | Fix/truncate corrupt tail; never skip silently in verify |
| `SCHEMA_INVALID` | Fails envelope schema | Reject run for v1 replay |
| `SEQUENCE_GAP` / `SEQUENCE_DUP` | Non-monotonic sequence | Hard fail; log is not a valid v1 capture |
| `CAUSATION_INVALID` | `causation_id` not prior | Hard fail |
| `CHAIN_BREAK` | `previous_event_sha256` ≠ fold head | Tamper or truncated copy |
| `HASH_MISMATCH` | Recomputed digest ≠ logged | Tamper or non-canonical writer |
| `ID_MISMATCH` | `event_id` ≠ `evt_`+digest | Non-conforming producer |
| `RESULT_HASH_MISMATCH` | `result_hash` ≠ payload.result | Corruption |
| `EVIDENCE_MISSING` | Content-address missing in store | Incomplete artifact bundle |
| `STATE_DIVERGENCE` | Reducer digest ≠ golden/expected | Bug in reducer vs producer, or golden drift |
| `RUN_ID_MIXED` | Multiple run_ids in one fold | Filter incorrectly |
| `AT_BEFORE_ROOT` | `at_sequence` without sequence 1 | Empty/invalid snapshot |
| `LEGACY_LOG` | Pre-v1 `PolicyDecision` rows | Use adapter or migrate first |

**Safety properties**

- Pure replay is **side-effect free** (no capability I/O).
- Verify-only is **side-effect free**.
- Failure MUST NOT append to the authoritative event log. Emitting `replay.completed` is a **separate** operator action on a different writer path (optional audit of the verify itself).

---

## 7. Golden test strategy

### Fixtures

Store under `tests/fixtures/replay/` (implementation slice):

```text
runs/
  allow_http/
    events.jsonl          # canonical lines
    evidence/             # content-addressed files
    golden/
      snapshot_end.json   # ReplayState public fields
      digests.jsonl       # {sequence, state_digest, event_sha256}
  deny_host/
    ...
  chain_tamper/
    events.jsonl          # mutated byte → expect CHAIN_BREAK / HASH_MISMATCH
  evidence_missing/
    events.jsonl          # ref without blob → EVIDENCE_MISSING
```

### Test matrix

| Test | Mode | Assert |
| --- | --- | --- |
| `test_pure_end_state_matches_golden` | pure | `snapshot.state == golden` and digests |
| `test_time_travel_prefix` | time_travel | for each checkpoint K, state@K matches golden digests |
| `test_verify_ok_on_canonical` | verify | `report.ok` |
| `test_verify_detects_bit_flip` | verify | `HASH_MISMATCH` or `CHAIN_BREAK` at expected sequence |
| `test_verify_detects_evidence_gap` | verify | `EVIDENCE_MISSING` |
| `test_sequence_gap_fails` | pure | `SEQUENCE_GAP` |
| `test_governance_posture_from_events` | pure | posture equals last `posture_after`, **not** live 60m window |
| `test_capability_not_invoked` | pure | monkeypatch capability registry; assert zero calls |
| `test_cross_machine_stable_digest` | pure | same fixtures → identical `state_digest` on two paths |
| `test_bisect_finds_first_divergence` | verify+golden | least failing sequence |

### Golden update policy

- Goldens are updated only with explicit `UPDATE_GOLDEN=1` (or script) after intentional reducer/SPEC changes.
- CI fails on digest drift.
- Fixtures MUST use canonical JSONL (sorted keys) so hash tests are stable.

### Minimal first vertical (implementation order)

1. Hash verify over a hand-canonical fixture (no reducer).
2. Reducer for `intent` → `governance.evaluated` → snapshot posture/graph.
3. Evidence presence checks.
4. Full type coverage + tamper fixtures.
5. CLI: `rif replay-run <run_id> --at N --mode verify|pure` (name TBD; do not break legacy `rif replay` until adapter exists).

---

## Relationship to current `src/rif_runtime/replay.py`

| Current | v1.0 engine |
| --- | --- |
| Reads `decisions.jsonl` | Reads `rif.runtime.event/v1` JSONL |
| Posture from all-time denial thresholds | Posture from logged `posture_after` (+ metrics `denial_count`) |
| No hash verification | Chain + event_id + result_hash |
| No time-travel index | `at_sequence` snapshots |
| Summary counts only | Full `ReplayState` + digests |

Legacy `recover()` remains until a migration adapter wraps old rows as synthetic `governance.evaluated` events.

---

## Complexity / API sketch (non-normative)

```text
class DeterministicReplayEngine:
    def pure(self, run_id, at_sequence=None) -> ReplayReport
    def verify(self, run_id, at_sequence=None, evidence_store=...) -> ReplayReport
    def snapshot(self, run_id, at_sequence) -> Snapshot
    def diff(self, run_id, a: int, b: int) -> StateDiff
    def bisect(self, run_id, predicate) -> int
```

Implementation lands in a later engineering slice; this document is the contract those APIs must obey.
