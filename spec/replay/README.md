# spec/replay

Contract for replay: capturing a runtime execution and re-running it (deterministic
or model-dependent) to verify behavior, diff against a prior run, or produce an
audit timeline.

**Placeholder** — no schema yet. Current replay logic lives in
`src/rif_runtime/replay.py` without a standalone contract; extracting one is the
next concrete step for this directory, per ADR-0008.

## Next slice
Define a `replay_capture.schema.json` describing the minimal shape a capture must
have (inputs, environment, timestamps, and evidence references) to be replayable.
