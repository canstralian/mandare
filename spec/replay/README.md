# spec/replay

Deterministic **replay engine** contract for RIF Runtime v1.0.

| File | Role |
| --- | --- |
| [`SPEC.md`](./SPEC.md) | State machine, algorithm, pseudocode, structures, complexity, failures, golden tests |
| [`replay_report.schema.json`](./replay_report.schema.json) | JSON Schema for replay/verify reports |

**Event unit:** [`../events/SPEC.md`](../events/SPEC.md) (`rif.runtime.event/v1`).

**Modes:** `pure` (reconstruct, no side effects), `verify` (hash/evidence checks), `time_travel` (state at sequence N).
