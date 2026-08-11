# Benchmark Engineer

## Mission

Own dataset quality evaluation: design and run benchmarks that measure whether a dataset build produces useful training signal.

---

## Responsibilities

- Quality benchmark design and execution
- Correlation analysis between heuristic quality scores and training outcomes
- Evaluation dataset curation and maintenance
- Research on quality measurement methodologies
- Maintaining `docs/research/QUALITY_BENCHMARKS.md`
- Per-build quality reports for publication approval

---

## Benchmark types

### Heuristic score calibration

Compares heuristic quality scores against human-labeled quality assessments.

For a calibration sample (200–500 chunks):
1. Score with `heuristic_scorer`.
2. Have a domain expert label as `high`, `medium`, or `low` quality.
3. Compute precision/recall of the scorer at the recommended threshold.
4. Report AUC of scorer vs. human labels.

Calibration must be performed when:
- A new content type is added to the pipeline
- The heuristic scorer weights are changed
- A new source dataset is added to the registry

### Training outcome correlation

Measures whether dataset quality scores predict training performance.

Requires a training run. Out of scope for the current Dataset Foundry implementation; tracked as future work.

### Coverage analysis

Verifies that a build covers the intended distribution of topics, tasks, and difficulty levels.

For evaluation datasets:
1. Sample 100 chunks from each decile of the quality score distribution.
2. Verify that all deciles are represented in the export.
3. Verify that the output covers the intended task types (e.g., all programming languages for a code dataset).

---

## Evaluation dataset requirements

An evaluation dataset built with the `evaluation` profile must:

- Have `min_quality_score >= 0.70` (higher threshold than SFT/DPO)
- Have a `ground_truth` annotation on every chunk
- Have no duplicate input/output pairs (exact deduplication is required)
- Have a documented difficulty distribution if used for difficulty-stratified evaluation

---

## Benchmark execution

```bash
rif-dataset benchmark \
  --build <build_id> \
  --sample-size 200 \
  --output /data/benchmarks/<build_id>/
```

Produces:
- `calibration_report.json`: heuristic score vs. human label comparison
- `coverage_report.json`: topic/task/difficulty distribution
- `anomaly_report.json`: outliers, unexpected distributions

---

## Publication gate

No dataset build is published to HuggingFace Hub without a benchmark report.

The benchmark report must be attached to the `DatasetBuild` artifact:

```python
DatasetBuild(
    ...
    benchmark_report_path="data/benchmarks/<build_id>/calibration_report.json",
)
```

If a benchmark report is absent, the `rif-dataset publish` command refuses to proceed.

---

## Research obligations

The Benchmark Engineer maintains:

- Score distribution baselines for all registered datasets (`docs/research/QUALITY_BENCHMARKS.md`)
- Threshold recommendations by profile and content type
- Documented failure modes for heuristic scoring
- A backlog of quality measurement methodologies to evaluate
