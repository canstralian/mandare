# Event Contract Inventory

Enumeration of every event/record type currently emitted by the running
`src/rif_runtime/` implementation: its schema, emitter, correlation key,
persistence, and downstream consumers. This is a snapshot of what the code
does today — it is the input needed for Section 5 ("Event Contract
Implications") and Section 11 ("event-type enumeration and
downstream-consumer inventory") of
`docs/spec-review-identity-spine-migration.md`, but scoped to this repository
as it actually exists (no `execution_id`, no database — see Gotchas in
`CLAUDE.md`).

## Correlation key today

There is no `run_id` or `execution_id` in this codebase. Every event below
correlates on `(actor, target)` (graph edges) or is simply appended in
timestamp order (JSONL logs). This is the baseline the identity-spine spec
would migrate away from.

## Event types

| # | Event | Schema (Pydantic/dataclass) | Emitted by | Correlation key today | Persisted to | Downstream consumers |
|---|---|---|---|---|---|---|
| 1 | Policy decision | `PolicyDecision` (`schemas.py:29`) | `PolicyEngine.evaluate()` via `RIFRuntime.evaluate()` / `record_decision()` (`runtime.py:45`) | `actor` + `target` (no id field) | `data/decisions.jsonl` (`JsonlStore`) | `GovernanceGraph.record_decision()`, `ReflexiveLoop.observe()` → `TelemetryStore`, `/v1/policy/evaluate`, `/v1/audit`, `/v1/persistence/summary`, `ReplayEngine` |
| 2 | Posture transition | ad-hoc `dict` (`old_posture`, `new_posture`) — no schema class | `RIFRuntime.record_decision()` / `evaluate_metasploit()` (`runtime.py:76-79`, `114-117`), only on change | none (append-only, order-correlated) | `data/posture_history.jsonl` | `/v1/persistence/summary`, `ReplayEngine` |
| 3 | Governance graph edge | `nx.MultiDiGraph` edge attrs (`decision`, `rule`, `environment`, `posture`, `timestamp`) | `GovernanceGraph.record_decision()` (`graph/memory.py:12`) | `(actor, target)` edge key | in-memory only (not persisted) | `/v1/graph/summary`, `graph/relationships.py` query helpers |
| 4 | Telemetry event | `PolicyDecision` held in a bounded `deque` | `TelemetryStore.record()` (`governance/telemetry.py:13`) | none (rolling window by `timestamp`) | in-memory only (max 1000, dropped oldest-first) | `PostureManager.next_posture()` (denial-count escalation), `/v1/telemetry/summary` |
| 5 | Metasploit evidence event | `EvidenceEvent` (`mcp/metasploit.py:154`) | `MetasploitGovernor.evaluate()` via `RIFRuntime.evaluate_metasploit()` (`runtime.py:112`) | `decision_id` (event-local UUID; not shared with `PolicyDecision`) | `data/metasploit_evidence.jsonl` | none in-repo yet (no reader found for this file) |
| 6 | Capability token issuance | `CapabilityToken` (`mcp/metasploit.py:113`) | `MetasploitGovernor.mint_token()` via `/v1/mcp/metasploit/token` | `token_id` | not persisted (returned to caller only) | `MetasploitGovernor.evaluate()` (token validation on the lab-broker lane) |

## Schema versions

None of the six event types above carry a `schema_version` field. This
contrasts with the two already-versioned contracts seeded from
`contracts/rif_familiar/` into `spec/`:

- `spec/governance/posture_decision.schema.json` — `rif-familiar.posture-decision/v0.1`
- `spec/evidence/observation_event.schema.json` — `rif-familiar.observation-event/v0.1`

Those two are device-facing (RIF Familiar) contracts and are **not** what the
Python runtime emits; they are the target shape referenced by
`spec/governance/README.md` and `spec/evidence/README.md` as "next slice"
work, not yet implemented against events #1–#6 above.

## Dry-run (non-recording) paths

Two routes intentionally produce a `PolicyDecision`/outcome without emitting
any of the above events (`record=False`): `POST /v1/mcp/invoke` and
`POST /v1/mcp/metasploit/evaluate`. These exist so unauthenticated simulation
requests cannot drive posture escalation or write to the audit trail
(`runtime.py:53-58`, `99-103`).

## Gaps relative to the identity-spine spec (Section 5 checklist)

- [x] Enumerated every event type currently emitted (this document, events #1–#6).
- [ ] None of these events emit `execution_id` today, so there is nothing to
      re-key — the migration described in
      `docs/spec-review-identity-spine-migration.md` presupposes entities
      (`GovernanceLedger`, `execution_id`-keyed tables, Supabase persistence)
      that do not exist in this repository. That document should be treated
      as a target-state spec for a different/future persistence layer, not a
      description of the current codebase.
- [ ] No event type here carries a `schema_version`; adding one is a
      prerequisite for any future versioned migration (per the "Run
      Observation / Execution Record / Evaluation Record versioning
      convention" referenced in Section 5).
- [ ] Event #5 (Metasploit evidence) has no in-repo downstream consumer or
      reader yet — flagged for follow-up before it is treated as load-bearing
      evidence.
