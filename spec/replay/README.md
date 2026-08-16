# spec/replay

Contract for replay: capturing a runtime execution and re-running it (deterministic
or model-dependent) to verify behavior, diff against a prior run, or produce an
audit timeline.

**Placeholder** — no schema yet. Current replay logic lives in
`src/rif_runtime/replay.py` without a standalone contract; extracting one is the
next concrete step for this directory, per ADR-0008.

## Normative constraint (pending extraction)

`docs/spec-review-capability-snapshot-authority.md` §6 states normatively that
**replay is not recovery**: replay reconstructs history and MUST be side-effect
free; recovery continues execution and may produce new Executions and effects.
The two MUST NOT share an API surface. `src/rif_runtime/replay.py` satisfies this
today, but only incidentally — the constraint is not yet expressed as a contract
here. Extracting it is part of this directory's next slice.

That review also constrains replay inputs: evaluation evidence (any judge or
scorer output) MUST NOT be an input to replay (§5), and recovery MUST NOT
implicitly re-observe capabilities (§6).

## Next slice
Define a `replay_capture.schema.json` describing the minimal shape a capture must
have (inputs, environment, timestamps, and evidence references) to be replayable —
including the `capability_snapshot_id` the captured decision was authorized
against, without which a capture is not reconstructable.
