# Skill: benchmark_dataset

## Purpose

Evaluate the quality and coverage of a completed `DatasetBuild`.

## When to use

- Before approving a build for publication
- When calibrating the heuristic scorer against human labels
- When comparing two builds of the same dataset with different profiles or thresholds
- After the Quality Reviewer identifies an anomaly in the quality report

## Inputs

| Input | Type | Description |
| --- | --- | --- |
| `build_id` | string | ID of a completed `DatasetBuild` |
| `sample_size` | int | Number of chunks to sample for human review. Default: 200 |
| `output_path` | string | Directory for benchmark output files |

## Preconditions

- `DatasetBuild` exists and `rif-dataset verify-build <build_id>` passes
- `DatasetManifest` for the build is accessible
- Quality scores are present on all chunks (`quality_score` annotation)

## Execution steps

1. Load the `DatasetBuild` and `DatasetManifest`.
2. Load the export artifact and reconstruct chunks.
3. **Score calibration**:
   a. Sample `sample_size` chunks stratified by quality decile.
   b. Write sampled chunks to `output_path/calibration_sample.jsonl` for human review.
   c. After human labels are provided (see note), compute precision/recall and AUC.
4. **Coverage analysis**:
   a. Compute content type distribution.
   b. Compute source dataset contribution by record count.
   c. Compute quality score distribution by content type and source.
   d. Flag any content type or source with <5% representation.
5. **Anomaly detection**:
   a. Flag bimodal score distributions.
   b. Flag sources with >30% of total excluded chunks.
   c. Flag content types with exclusion rate outside expected range.
6. Write reports to `output_path/`.

## Outputs

| File | Description |
| --- | --- |
| `calibration_sample.jsonl` | Sampled chunks for human quality labeling |
| `calibration_report.json` | Scorer precision/recall vs. human labels (after labeling) |
| `coverage_report.json` | Distribution by content type, source, quality |
| `anomaly_report.json` | Flagged distributions and outliers |

## Human labeling step

The calibration sample must be reviewed by a domain expert before `calibration_report.json` can be produced.

Labeling protocol:
- Label each chunk as `high`, `medium`, or `low` quality
- Use `high` for chunks you would want in a training dataset
- Use `low` for chunks you would exclude (noise, boilerplate, truncated, low-information)
- Use `medium` for borderline cases

Write labels back to `calibration_sample_labeled.jsonl` (same format, add `"human_label"` field).

Then run:

```bash
rif-dataset benchmark --build <build_id> --apply-labels output_path/calibration_sample_labeled.jsonl
```

## Coverage thresholds

A build passes coverage analysis if:

- At least 2 content types are represented (for multi-type datasets)
- No single source contributes >70% of the total chunks
- Quality score P10 is above 0.30 (even the bottom decile is not pure noise)

## Anomaly flags

| Flag | Threshold | Meaning |
| --- | --- | --- |
| `bimodal_distribution` | Two peaks separated by >0.3 | Two quality populations; consider per-source thresholds |
| `source_concentration` | Single source >70% of chunks | Dataset dominated by one source |
| `high_exclusion_source` | Source contributes >30% of excluded chunks | Source has structural quality issue |
| `low_p10_score` | P10 < 0.30 | Bottom decile is likely noise |

## Publication gate

No build is published without passing `benchmark_dataset`:

- `calibration_report.json` must exist
- `anomaly_report.json` must show no unresolved critical flags
- Quality Reviewer must acknowledge the reports

Critical flags (`bimodal_distribution`, `high_exclusion_source`) require a written acknowledgment in the build's release notes before publication is approved.
