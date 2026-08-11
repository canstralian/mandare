# code_refinement_mst

Measures how long an agent keeps a solution functionally correct while RIF
governs repeated refinement instructions against it.

Background: CodeChat-Eval found that models lose functional correctness
across multi-turn refinement (correctness drops of 19.2%-69.2% depending on
model, worst for logic-level and additive changes). LoopCoder found iterative
loops only help when they're stabilized and evaluated as loops rather than
one-shot outputs. This eval treats refinement as a governed loop: every turn
is gated through RIF's policy engine, every test result is verified in an
isolated sandbox, and a regression is itself recorded as a governance event
that can escalate posture — RIF records the causal chain, not just the
output.

## Metric: MST-RIF

Mean Sustainable Turns before the first verified regression.

| Session   | Turns attempted | First failed turn | MST contribution |
| --------- | ---------------- | ------------------ | ----------------- |
| task_001  | 10                | 6                   | 5                  |
| task_002  | 10                | none                | 10                 |
| task_003  | 10                | 2                   | 1                  |

Higher MST-RIF means the agent preserves correctness longer under iterative
change.

## Layout

```
schema/             task / session / result JSON Schemas
tasks/python/        task definitions (prompt, tests, refinement_turns)
runners/
  sandbox_exec.py     isolated pytest execution of a candidate solution
  score.py            score_session() — the MST scorer
  run_session.py       orchestrates one task through governed refinement
sessions/generated/  per-run session traces (gitignored, written at runtime)
reports/              mst_report.json / mst_report.md (gitignored, written at runtime)
```

## The circuit

```
task -> generate_initial() -> for each refinement turn:
    RIFRuntime.evaluate(code.refine)      governance gate for the turn
    agent.refine()                        candidate code for this turn
    run_in_sandbox()                      isolated pytest run
    RIFRuntime.record_decision(deny)      if verification fails, recorded
                                           as a governed denial (drives
                                           posture escalation like any
                                           other denial)
-> score_session()  -> RIFCodeRefinementResult
```

Every turn emits a `code_refinement_turn` event (see
`schema/session.schema.json`) with before/after state hashes, the policy
decision, the verification outcome, and whether this turn was the first
regression in the session.

## Running a session

`run_session.py` does not embed a model client — it defines the governed
loop and leaves generation pluggable. Implement `CodeAgent`
(`generate_initial`, `refine`) against whatever model client you're
evaluating, then run:

```bash
python rif-evals/code_refinement_mst/runners/run_session.py \
  rif-evals/code_refinement_mst/tasks/python/task_001_palindrome.json \
  --agent your_module:YourCodeAgent
```

This writes a full session trace to `sessions/generated/` and upserts the
task/model row into `reports/mst_report.json` and `reports/mst_report.md`.

For exercising the harness itself without a live model, use
`ScriptedAgent` (a fixed sequence of code states) — see
`tests/test_code_refinement_mst.py` for an example that drives a forced
regression through the full circuit, including posture escalation.

## Constraint alignment gate

If a generation-time constrainer (e.g. JSON-schema-constrained decoding) is
ever layered on top of this eval, classify it first — incomplete
constrainers can make *unconstrained* decoding outperform constrained
decoding on functional correctness. Default policy:

```yaml
constraint_alignment:
  target_surface: python
  constrainer_type: json_schema
  completeness: partial
  soundness: high
  distortion_risk: medium
  recommended_mode: generate_then_validate
```

Rule: if `completeness != high`, don't force constrained decoding — use
generate -> validate -> repair instead.

## Adding tasks

A task is one JSON file under `tasks/python/` validating against
`schema/task.schema.json`: a prompt, an entrypoint function name, a list of
standalone assertion strings, and an ordered list of refinement turns
(`turn`, `instruction`, `change_type`). Start with one model and a handful
of tasks before comparing models — the first milestone is proving the
circuit is deterministic, not leaderboard quality.
