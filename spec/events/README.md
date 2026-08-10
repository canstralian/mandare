# spec/events

Canonical **RIF Runtime Event Model v1.0** (frozen).

| File | Role |
| --- | --- |
| [`SPEC.md`](./SPEC.md) | Normative principles, examples, versioning, determinism, trade-offs |
| [`event_envelope.schema.json`](./event_envelope.schema.json) | JSON Schema (draft 2020-12) for the envelope |

This domain is distinct from `spec/evidence/observation_event.schema.json` (Familiar device observations). Runtime governance/execution events use `rif.runtime.event/v1`.
