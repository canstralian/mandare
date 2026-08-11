# RIF Runtime Event Model v1.0 (Frozen)

**Status:** Frozen for v1.0 design (Track B contract).  
**Implements direction from:** ADR-0002 (audit events as canonical replay source).  
**Schema id:** `rif://contracts/runtime-event/v1`  
**Schema version string:** `rif.runtime.event/v1`

This document is the authoritative event model for RIF Runtime v1.0.  
Implementation under `src/rif_runtime/` must conform; it must not invent a competing envelope.

**Non-goals for this freeze:** wiring every event type into today's MVP evaluate path; Run-aggregate persistence (ADR-0010); Familiar device observation events (remain under `spec/evidence/observation_event.schema.json`).

**Relationship to current code:** Today's `PolicyDecision` JSONL rows are a **pre-v1.0 persistence shape**. v1.0 maps governance outcomes primarily to `governance.evaluated` (+ optional `capability.*` / `evidence.recorded`) inside this envelope. Migration is additive: export/rewrite tools may wrap legacy rows; replay of v1.0 requires this envelope.

---

## 1. Schema principles

1. **Append-only.** Events are never updated or deleted in place. Corrections are new events that reference prior `event_id`s.
2. **Envelope + typed payload.** Cross-cutting identity, causality, and integrity live in the envelope; domain fields live in `payload` discriminated by `type`.
3. **Deterministic identity.** `event_id` is derived from canonical content (see §5). Producers MUST NOT use random UUIDs as `event_id`.
4. **Sequence is causal order.** Within a `run_id`, `sequence` is the sole authoritative order. Wall-clock time is observational only.
5. **Attributable governance.** Every `governance.evaluated` MUST name actor, environment, posture before/after, matched rule, decision, and reason code.
6. **Evidence by reference.** Large blobs are not inlined; `evidence_refs` point at content-addressed artifacts or prior event ids.
7. **Forward-compatible payloads.** Unknown `payload` keys under a known `type` are rejected at write time for v1 (`additionalProperties: false` per type). New optional envelope fields require a minor schema bump; new event types require a minor bump; breaking envelope changes require a major bump (`v2`).
8. **JSONL-native.** One event = one JSON object = one line. Canonical serialization is UTF-8, JSON object key order as produced by the canonical encoder (see §5).
9. **Hash chain optional but defined.** `integrity.previous_event_sha256` + `integrity.event_sha256` enable tamper detection; genesis previous hash is 64 zero hex digits (same convention as `audit.GENESIS_HASH`).
10. **Separation of concerns.** Familiar `observation_event` remains device-facing. Runtime execution/governance uses this model. `evidence.recorded` may *reference* Familiar observation ids.

---

## 2. JSON schema for envelope

See [`event_envelope.schema.json`](./event_envelope.schema.json).

### Envelope fields (normative summary)

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | yes | Const `rif.runtime.event/v1` |
| `event_id` | yes | Deterministic id: `evt_` + 64 hex (sha256) |
| `type` | yes | Event type enum (below) |
| `run_id` | yes | Correlation root for one governed execution (`run_` + 32 hex) |
| `sequence` | yes | Monotonic integer ≥ 1 within `run_id` |
| `causation_id` | yes | `event_id` of direct cause, or equal to `event_id` for the root `intent.received` |
| `correlation_id` | yes | Defaults to `run_id`; may equal an external workflow id if prefixed `ext_` |
| `recorded_at` | yes | RFC 3339 UTC timestamp (observational; not used for ordering) |
| `actor` | yes | Who initiated or on whose behalf (`kind` + `id`) |
| `capability` | no | Capability identity when relevant |
| `budget` | no | Frozen budget snapshot at emit time |
| `evidence_refs` | yes | Array (may be empty) of evidence references |
| `result_hash` | no | sha256 of canonical JSON of `payload.result` when a result is present |
| `integrity` | yes | Hash-chain fields |
| `payload` | yes | Type-specific object |

### Event types (v1 closed set)

```text
intent.received
mode.selected
memory.retrieved
context.built
governance.evaluated
budget.debited
capability.requested
capability.granted
capability.denied
execution.started
execution.completed
execution.failed
evidence.recorded
replay.completed
```

---

## 3. JSON examples for every event type

Shared run: `run_id = run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`  
Root event id for intent shown as `evt_1111…` (illustrative; real ids MUST be derived per §5).

### intent.received

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_8f3c0a1b2c3d4e5f6789012345678901abcdef0123456789abcdef0123456789",
  "type": "intent.received",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 1,
  "causation_id": "evt_8f3c0a1b2c3d4e5f6789012345678901abcdef0123456789abcdef0123456789",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:00.000Z",
  "actor": { "kind": "agent", "id": "agent:orchestrator" },
  "evidence_refs": [],
  "integrity": {
    "previous_event_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "event_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  },
  "payload": {
    "intent_text": "fetch model docs",
    "intent_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "source": "api",
    "environment": "RIF_Runtime"
  }
}
```

### mode.selected

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa",
  "type": "mode.selected",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 2,
  "causation_id": "evt_8f3c0a1b2c3d4e5f6789012345678901abcdef0123456789abcdef0123456789",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:00.010Z",
  "actor": { "kind": "runtime", "id": "rif_runtime" },
  "evidence_refs": [],
  "integrity": {
    "previous_event_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "event_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
  },
  "payload": {
    "mode": "governed_execute",
    "reason_code": "DEFAULT_MODE",
    "posture": "normal"
  }
}
```

### memory.retrieved

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb",
  "type": "memory.retrieved",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 3,
  "causation_id": "evt_21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa21aa",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:00.020Z",
  "actor": { "kind": "runtime", "id": "rif_runtime" },
  "evidence_refs": [
    {
      "kind": "content_sha256",
      "id": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    }
  ],
  "integrity": {
    "previous_event_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "event_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
  },
  "payload": {
    "memory_backend": "none",
    "query_hash": "1212121212121212121212121212121212121212121212121212121212121212",
    "hit_count": 0,
    "item_hashes": []
  }
}
```

### context.built

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc",
  "type": "context.built",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 4,
  "causation_id": "evt_31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb31bb",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:00.030Z",
  "actor": { "kind": "runtime", "id": "rif_runtime" },
  "evidence_refs": [],
  "result_hash": "3434343434343434343434343434343434343434343434343434343434343434",
  "integrity": {
    "previous_event_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
    "event_sha256": "5656565656565656565656565656565656565656565656565656565656565656"
  },
  "payload": {
    "context_hash": "3434343434343434343434343434343434343434343434343434343434343434",
    "token_estimate": 0,
    "includes": ["intent", "environment", "posture"]
  }
}
```

### governance.evaluated

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd",
  "type": "governance.evaluated",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 5,
  "causation_id": "evt_41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc41cc",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:00.040Z",
  "actor": { "kind": "agent", "id": "agent:orchestrator" },
  "capability": {
    "id": "http.request",
    "version": "1",
    "action": "http.request",
    "target": "https://api.anthropic.com/v1/messages"
  },
  "budget": {
    "requests_remaining": 99,
    "tokens_remaining": 100000,
    "cost_remaining_usd": "10.00"
  },
  "evidence_refs": [],
  "integrity": {
    "previous_event_sha256": "5656565656565656565656565656565656565656565656565656565656565656",
    "event_sha256": "7878787878787878787878787878787878787878787878787878787878787878"
  },
  "payload": {
    "decision": "allow",
    "reason_code": "NETWORK_HOST_ALLOWED",
    "reason_summary": "host is in environment allowlist",
    "matched_rule": "policy.allow_known_model_hosts",
    "environment": "RIF_Runtime",
    "posture_before": "normal",
    "posture_after": "normal",
    "precedence": ["posture", "policy", "mcp", "package", "network", "default"],
    "environment_snapshot_hash": "9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a9a",
    "request": {
      "actor": "agent:orchestrator",
      "action": "http.request",
      "target": "https://api.anthropic.com/v1/messages"
    }
  }
}
```

### budget.debited

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_61ee61ee61ee61ee61ee61ee61ee61ee61ee61ee61ee61ee61ee61ee61ee61ee",
  "type": "budget.debited",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 6,
  "causation_id": "evt_51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:00.050Z",
  "actor": { "kind": "runtime", "id": "rif_runtime" },
  "budget": {
    "requests_remaining": 98,
    "tokens_remaining": 100000,
    "cost_remaining_usd": "10.00"
  },
  "evidence_refs": [],
  "integrity": {
    "previous_event_sha256": "7878787878787878787878787878787878787878787878787878787878787878",
    "event_sha256": "9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c"
  },
  "payload": {
    "debit": { "requests": 1, "tokens": 0, "cost_usd": "0.00" },
    "reason_code": "GOVERNANCE_ALLOW",
    "related_event_id": "evt_51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd"
  }
}
```

### capability.requested

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff",
  "type": "capability.requested",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 7,
  "causation_id": "evt_51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:00.060Z",
  "actor": { "kind": "agent", "id": "agent:orchestrator" },
  "capability": {
    "id": "http.request",
    "version": "1",
    "action": "http.request",
    "target": "https://api.anthropic.com/v1/messages"
  },
  "evidence_refs": [],
  "integrity": {
    "previous_event_sha256": "9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c",
    "event_sha256": "aeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeae"
  },
  "payload": {
    "args_hash": "b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0",
    "governance_event_id": "evt_51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd"
  }
}
```

### capability.granted

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_8200820082008200820082008200820082008200820082008200820082008200",
  "type": "capability.granted",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 8,
  "causation_id": "evt_71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:00.070Z",
  "actor": { "kind": "runtime", "id": "rif_runtime" },
  "capability": {
    "id": "http.request",
    "version": "1",
    "action": "http.request",
    "target": "https://api.anthropic.com/v1/messages"
  },
  "evidence_refs": [],
  "integrity": {
    "previous_event_sha256": "aeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeaeae",
    "event_sha256": "c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1"
  },
  "payload": {
    "grant_token_hash": "d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2",
    "expires_at": "2026-08-10T14:05:00.000Z",
    "governance_event_id": "evt_51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd"
  }
}
```

### capability.denied

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_9300930093009300930093009300930093009300930093009300930093009300",
  "type": "capability.denied",
  "run_id": "run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "sequence": 5,
  "causation_id": "evt_71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff71ff",
  "correlation_id": "run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "recorded_at": "2026-08-10T14:01:00.000Z",
  "actor": { "kind": "agent", "id": "agent:test" },
  "capability": {
    "id": "http.request",
    "version": "1",
    "action": "http.request",
    "target": "https://blocked.example.com"
  },
  "evidence_refs": [],
  "integrity": {
    "previous_event_sha256": "e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3",
    "event_sha256": "f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4"
  },
  "payload": {
    "reason_code": "NETWORK_HOST_DENIED",
    "matched_rule": "network.host.denied",
    "governance_event_id": "evt_51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd51dd"
  }
}
```

### execution.started

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_a400a400a400a400a400a400a400a400a400a400a400a400a400a400a400a400",
  "type": "execution.started",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 9,
  "causation_id": "evt_8200820082008200820082008200820082008200820082008200820082008200",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:00.080Z",
  "actor": { "kind": "runtime", "id": "rif_runtime" },
  "capability": {
    "id": "http.request",
    "version": "1",
    "action": "http.request",
    "target": "https://api.anthropic.com/v1/messages"
  },
  "evidence_refs": [],
  "integrity": {
    "previous_event_sha256": "c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1",
    "event_sha256": "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5"
  },
  "payload": {
    "execution_id": "exec_11111111111111111111111111111111",
    "manifest_hash": "b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6b6",
    "grant_event_id": "evt_8200820082008200820082008200820082008200820082008200820082008200"
  }
}
```

### execution.completed

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_b500b500b500b500b500b500b500b500b500b500b500b500b500b500b500b500",
  "type": "execution.completed",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 10,
  "causation_id": "evt_a400a400a400a400a400a400a400a400a400a400a400a400a400a400a400a400",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:01.000Z",
  "actor": { "kind": "runtime", "id": "rif_runtime" },
  "capability": {
    "id": "http.request",
    "version": "1",
    "action": "http.request",
    "target": "https://api.anthropic.com/v1/messages"
  },
  "evidence_refs": [
    {
      "kind": "content_sha256",
      "id": "c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7"
    }
  ],
  "result_hash": "d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8",
  "integrity": {
    "previous_event_sha256": "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5",
    "event_sha256": "e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9"
  },
  "payload": {
    "execution_id": "exec_11111111111111111111111111111111",
    "status": "succeeded",
    "result": { "http_status": 200 },
    "duration_ms": 920
  }
}
```

### execution.failed

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_c600c600c600c600c600c600c600c600c600c600c600c600c600c600c600c600",
  "type": "execution.failed",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 10,
  "causation_id": "evt_a400a400a400a400a400a400a400a400a400a400a400a400a400a400a400a400",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:01.000Z",
  "actor": { "kind": "runtime", "id": "rif_runtime" },
  "capability": {
    "id": "http.request",
    "version": "1",
    "action": "http.request",
    "target": "https://api.anthropic.com/v1/messages"
  },
  "evidence_refs": [],
  "result_hash": "f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0",
  "integrity": {
    "previous_event_sha256": "a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5",
    "event_sha256": "0101010101010101010101010101010101010101010101010101010101010101"
  },
  "payload": {
    "execution_id": "exec_11111111111111111111111111111111",
    "error_code": "TRANSPORT_TIMEOUT",
    "error_summary": "upstream timed out",
    "retryable": true,
    "result": { "error_code": "TRANSPORT_TIMEOUT" }
  }
}
```

### evidence.recorded

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_d700d700d700d700d700d700d700d700d700d700d700d700d700d700d700d700",
  "type": "evidence.recorded",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 11,
  "causation_id": "evt_b500b500b500b500b500b500b500b500b500b500b500b500b500b500b500b500",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-10T14:00:01.050Z",
  "actor": { "kind": "runtime", "id": "rif_runtime" },
  "evidence_refs": [
    {
      "kind": "content_sha256",
      "id": "c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7"
    }
  ],
  "integrity": {
    "previous_event_sha256": "e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9e9",
    "event_sha256": "0202020202020202020202020202020202020202020202020202020202020202"
  },
  "payload": {
    "evidence_kind": "execution_output",
    "content_sha256": "c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7c7",
    "media_type": "application/json",
    "related_event_id": "evt_b500b500b500b500b500b500b500b500b500b500b500b500b500b500b500b500",
    "redaction": "none"
  }
}
```

### replay.completed

```json
{
  "schema_version": "rif.runtime.event/v1",
  "event_id": "evt_e800e800e800e800e800e800e800e800e800e800e800e800e800e800e800e800",
  "type": "replay.completed",
  "run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "sequence": 12,
  "causation_id": "evt_8f3c0a1b2c3d4e5f6789012345678901abcdef0123456789abcdef0123456789",
  "correlation_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "recorded_at": "2026-08-11T10:00:00.000Z",
  "actor": { "kind": "operator", "id": "human:auditor" },
  "evidence_refs": [],
  "result_hash": "0303030303030303030303030303030303030303030303030303030303030303",
  "integrity": {
    "previous_event_sha256": "0202020202020202020202020202020202020202020202020202020202020202",
    "event_sha256": "0404040404040404040404040404040404040404040404040404040404040404"
  },
  "payload": {
    "replay_mode": "deterministic_verify",
    "source_run_id": "run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "events_replayed": 11,
    "matched": true,
    "diff_hash": null,
    "result": { "matched": true, "events_replayed": 11 }
  }
}
```

Illustrative digests above use patterned hex for readability. Conforming producers MUST compute real SHA-256 digests per §5.

---

## 4. Versioning strategy

| Change | Version impact | Mechanism |
| --- | --- | --- |
| New optional envelope field | Minor (`v1.1` string or nested `schema_version`) | Additive; readers ignore unknown envelope fields only after a published minor that declares them |
| New event `type` | Minor | Add to enum in a new schema file revision; old readers reject unknown types (safe fail) |
| New required envelope field / rename / remove | Major (`rif.runtime.event/v2`) | New `$id`; dual-write or migrate offline |
| Payload field additive within a type | Minor | Prefer optional fields; never reuse names with new meaning |
| Payload semantic break | Major or new type name | Prefer new `type` over overloading |

**Compatibility rules**

- Writers emit exactly one `schema_version` per line.
- Readers MUST reject lines with unknown major version.
- JSONL files MAY contain a mix of `v1` and later majors only during controlled migration windows; replay tools MUST pin expected version(s).
- Familiar observation events (`rif-familiar.observation-event/v0.1`) are **not** versioned together with this envelope; cross-link via `evidence_refs.kind = "observation_event_id"`.

**Storage layout (recommended)**

```text
data/events/<run_id>.jsonl   # append-only per run
data/events/_index.jsonl     # optional: run_id, head_hash, sequence_max (derived)
```

Legacy `data/decisions.jsonl` remains until a migration tool emits `governance.evaluated` envelopes.

---

## 5. Determinism guarantees

### Guaranteed

1. **Same inputs → same `event_id` and `integrity.event_sha256`.**  
   Given identical `run_id`, `sequence`, `type`, canonical `payload`, `actor`, optional `capability`/`budget`/`evidence_refs`/`result_hash`, and `integrity.previous_event_sha256`, two machines produce identical `event_id` and `event_sha256`.
2. **Order.** Replay sorts strictly by `(run_id, sequence)`. Ties are a protocol violation.
3. **Causality.** For `sequence > 1`, `causation_id` MUST equal some prior `event_id` in the same run with lower `sequence`. Root: `type=intent.received`, `causation_id=event_id`.
4. **Governance attribution.** `governance.evaluated.payload` MUST include actor request, decision, matched_rule, reason_code, environment, posture_before/after.
5. **Result binding.** If `payload` contains `result`, `result_hash` MUST equal SHA-256 of canonical JSON of that object.
6. **Cross-machine replay of governance.** Reconstructing posture/graph from the event log uses only envelope+payload fields — never wall clock, never process-local posture memory.

### Explicitly NOT guaranteed

1. **`recorded_at` equality across machines** — observational only.
2. **Bit-identical JSONL whitespace/key order from non-canonical encoders** — producers MUST use the canonical encoder below for hashing; stored lines SHOULD be canonical.
3. **Model/tool nondeterminism inside execution** — `execution.completed` records hashes of observed results; re-execution may diverge unless capability is pure. `replay.completed.matched` reports verify-vs-capture, not magical determinism of external systems.
4. **Legacy `PolicyDecision.timestamp` / `uuid4` explainability ids** — pre-v1.0 shapes are outside these guarantees.

### Canonicalization algorithm (normative)

1. Build the **hash preimage object** excluding `event_id` and `integrity.event_sha256` (include `integrity.previous_event_sha256`).
2. Serialize with:
   - UTF-8
   - JSON object keys sorted lexicographically at every level
   - No insignificant whitespace
   - Numbers as JSON numbers (no `1.0` vs `1` coercion — budgets that need decimal use **strings**)
   - Reject `NaN`/`Infinity`
3. `event_sha256 = hex(sha256(utf8_bytes))`
4. `event_id = "evt_" + event_sha256`  
   (Full 64 hex keeps collision resistance; prefix is for operability.)
5. `run_id` for a new run: either client-supplied opaque `run_`+32 hex, or  
   `run_` + first 32 hex of `sha256(canonical(intent_hash|actor.id|environment|schema_version))` when the producer needs a derived id. Client-supplied ids MUST be stable for replay.

### Mapping from today's MVP

| Today | v1.0 event |
| --- | --- |
| `PolicyRequest` + `PolicyDecision` append | `governance.evaluated` (+ optional `capability.denied`/`granted`) |
| Metasploit evidence JSONL | `evidence.recorded` + refs |
| `ReplayEngine.recover()` summary | Derived view; emit `replay.completed` when a verify pass finishes |
| In-memory posture | Reconstructed from `governance.evaluated` posture_after chain |

---

## 6. Trade-offs

| Choice | Benefit | Cost |
| --- | --- | --- |
| Closed v1 type enum | Replayers and auditors know the world | New lifecycle steps need a minor schema bump |
| Derived `event_id` = hash | Cross-machine identity; no uuid4 | Cannot mint id before payload is final; retries must be idempotent |
| `sequence` over wall clock | True causal order / merge safety within a run | Requires a single writer per `run_id` (or reserved sequence allocator) |
| Decimal budgets as strings | Avoid JSON number drift | Slightly awkward for consumers |
| Hash chain in every event | Tamper evidence without a separate audit store | Extra CPU; chain breaks on partial file copy unless head is tracked |
| Separate Familiar observation schema | Keeps device privacy contract stable | Two event worlds; must cross-link carefully |
| Freeze before full wiring | Unblocks deterministic v1.0 design | MVP still writes legacy `decisions.jsonl` until an implementation slice lands |
| Attributable governance in payload | Meets “every decision attributable” | Larger events than bare allow/deny |

### Risks if ignored

- Continuing to persist only `PolicyDecision` with `datetime.now` / process posture will **not** satisfy this freeze.
- Emitting these types without canonical hashing will **break** cross-machine replay.
- Treating `recorded_at` as ordering will reintroduce the live-vs-replay posture bug class.

---

## Implementation notes (non-normative)

1. Next engineering slice: event writer + JSON Schema validation tests under `tests/`; do not expand API surface until writer exists.
2. Update `spec/replay/README.md` to require this envelope as the capture unit.
3. ADR follow-up: accept this freeze as the runtime event contract superseding ad-hoc JSONL row shapes for v1.0+.
