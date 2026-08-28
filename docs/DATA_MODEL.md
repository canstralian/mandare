# Mandare — Data Model Proposal

> **Status: draft design.** This document describes a possible relational/Supabase persistence model. It is **not** the schema of the current default runtime and must not be used as evidence that the proposed tables, RLS policies, migrations, or invariants are implemented.

## Why this document exists

The runtime currently uses local JSON/JSONL persistence for core state. The repository also contains an optional Supabase integration for execution/evidence writes and JWT verification. This document explores how a future durable relational model could represent that state without silently changing authority semantics.

## Design principles

Any future persistent model should preserve:

1. **Authority separation** — storage must not become an implicit policy authority.
2. **Provenance** — records should distinguish observed facts, derived state, proposals, and approvals.
3. **Replay semantics** — the schema must define what can be reconstructed and what cannot.
4. **Tenant/scope boundaries** — access controls must be explicit rather than inferred from application conventions.
5. **Migration safety** — every schema change needs compatibility, backfill, rollback, and fixture strategy.
6. **Data minimization** — sensitive prompts, credentials, tokens, and model payloads should not be persisted merely because the schema can hold them.

## Candidate entities

The following are design candidates, not current runtime guarantees:

- `projects` — logical tenancy/scope;
- `users` — human principals;
- `agents` — non-human actors;
- `models` — model/provider registry;
- `sessions` — governed working context;
- `policies` — declarative policy records;
- `executions` — governed action/decision records;
- `execution_logs` — operational logs;
- `artifacts` — produced files/reports;
- `memories` — scoped durable memory;
- `evaluations` — human/model assessments.

## Current-to-future mapping

| Current state | Candidate future representation | Status |
|---|---|---|
| `data/policies.json` | `policies` | Design mapping |
| `decisions.jsonl` | `executions` or a dedicated decision/event table | Design mapping |
| `posture_history.jsonl` | posture-event history | Design mapping |
| `metasploit_evidence.jsonl` | evidence/event records | Design mapping |
| Supabase `execution_runs` helper | execution/run record | Partially represented by optional integration |
| Supabase `evidence_ledger` helper | evidence record | Partially represented by optional integration |

## Open design questions

Before migrations are implemented, the project must settle:

- whether `execution` or `run` is the aggregate root;
- whether policy decisions and execution outcomes are separate event types;
- what makes an evidence record authoritative;
- how identity maps between local runtime actors and external identity providers;
- what replay means after migration;
- which data is retained, redacted, encrypted, or deleted;
- how append-only semantics are enforced and independently verified;
- how RLS and service-role boundaries map to the actual threat model;
- how fixture data is versioned and migrated;
- how a failed remote persistence write affects local authority and operator visibility.

## Proposed migration discipline

A future database migration should not land merely because the SQL is valid. It should include:

```text
contract
  -> fixture inventory
  -> migration
  -> backfill test
  -> replay/recovery test
  -> authorization/RLS test
  -> rollback plan
  -> staged deployment
```

Until that work is complete, the file-backed runtime remains the implementation reference for local persistence.

## Non-goals

This document does not establish:

- a production Supabase deployment;
- RLS coverage that has not been implemented and tested;
- immutable database storage;
- regulatory compliance;
- distributed transaction guarantees;
- a migration compatibility promise.

Those are separate engineering claims that require separate evidence.
