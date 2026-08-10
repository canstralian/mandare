# spec/replay

Contract for replay: capturing a runtime execution and re-running it (deterministic
or model-dependent) to verify behavior, diff against a prior run, or produce an
audit timeline.

**Placeholder** — capture/diff schemas not yet extracted. The **event unit of
replay** is frozen in [`../events/SPEC.md`](../events/SPEC.md)
(`rif.runtime.event/v1`). Next slice: define `replay_capture.schema.json` as an
ordered sequence of those envelopes plus verify metadata (`replay.completed`).
