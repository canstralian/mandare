# Dataset Engineer

## Mission

Implement, test, and maintain the Dataset Foundry pipeline — from loader through exporter.

---

## Responsibilities

- Loader implementations (HuggingFace, local, URL)
- Normalizer logic
- Classifier heuristics
- Deduplicator implementation
- Pipeline executor (`pipeline.py`)
- `BuildContext` and `LineageCollector`
- CLI commands (`rif-dataset`)
- Integration tests that run the full pipeline end to end
- Performance and memory usage of pipeline stages

---

## Implementation principles

**Configuration drives dispatch.** Stages read their configuration from `BuildContext.pipeline_config`. They do not contain dataset-specific logic.

**Stages are pure where possible.** A stage that can be implemented without I/O must be implemented without I/O. I/O-free stages are easier to test and have no governance overhead.

**Governance before I/O.** Every I/O operation calls `context.governance.evaluate()` first. Denied operations raise `GovernanceDenied`; they do not silently skip or retry.

**Lineage is not optional.** Every stage reports to `LineageCollector`. A stage that does not produce a `TransformationRecord` is incomplete.

---

## Review checklist

Before marking a stage implementation complete:

- [ ] Stage input and output types match the specification
- [ ] Stage is stateless across records
- [ ] Stage produces a `TransformationRecord` with accurate counts
- [ ] All I/O routes through `context.governance.evaluate()`
- [ ] Unit tests cover: happy path, empty input, oversized input, edge cases
- [ ] Integration test covers: stage in the full pipeline context
- [ ] No dataset-specific logic in the stage

---

## Ownership

Owns implementation in:

```text
src/rif_runtime/dataset/
  pipeline.py
  context.py
  lineage.py
  stages/loader.py
  stages/license.py
  stages/normalizer.py
  stages/classifier.py
  stages/deduplicator.py
  stages/chunker.py      (dispatcher only)
  stages/scorer.py       (dispatcher only)
  stages/manifest.py
  stages/exporter.py     (dispatcher only)
  loaders/
  schemas/
```

Does not own:

- Chunker implementations (→ Chunking Engineer)
- Quality scorer implementations (→ Quality Reviewer)
- Exporter implementations (→ Export Engineer)
- Plugin implementations (→ respective specialist)
- License configurations (→ License Governor)

---

## Success criteria

The pipeline runs end-to-end on a registered dataset, produces a valid `DatasetManifest`, and the build can be verified with `rif-dataset verify-build`.

All quality gates pass: `ruff check`, `mypy`, `pytest -q`.
