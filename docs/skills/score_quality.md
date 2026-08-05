# Skill: score_quality

## Purpose

Apply the configured quality scorer to each `DatasetChunk` and annotate it with a quality score.

## When to use

- As part of the full build pipeline (after chunking, before manifest generation)
- When calibrating scorer thresholds against a sample
- When comparing two scorers on the same dataset

## Inputs

| Input | Type | Description |
| --- | --- | --- |
| `chunks` | `Iterable[DatasetChunk]` | Chunks from the Chunking stage |
| `scorer_id` | string | Quality scorer config ID |
| `context` | `BuildContext` | Pipeline context (for governance if scorer requires I/O) |

## Preconditions

- Chunks are fully constructed (text, char_count, content_type set)
- Scorer config exists in `configs/quality/<scorer_id>.yaml`
- If scorer is a plugin requiring network: RIF Runtime is running and the endpoint is in the allowed hosts policy

## Execution steps

1. Load scorer config and instantiate the scorer.
2. For each chunk:
   a. If scorer requires I/O: call `context.governance.evaluate("READ", endpoint)`.
   b. Call `scorer.score(chunk, context)`.
   c. Add `quality_score` annotation to the chunk.
   d. Compute `token_count` if not already set (used for size-based quality signals).
3. Collect scores and compute distribution statistics.
4. Return scored chunks and a `QualityReport`.

## Outputs

| Output | Type | Description |
| --- | --- | --- |
| `chunks` | `Iterable[DatasetChunk]` | Chunks with `quality_score` annotation |
| `report` | `DatasetQualityReport` | Score distribution, mean, median |

## Score annotation format

```python
Annotation(
    key="quality_score",
    value={
        "score": 0.74,
        "scorer_id": "heuristic_scorer",
        "scored_at": "2026-08-05T12:00:00Z",
    },
    source="quality_scorer",
)
```

## Validation

After scoring:

- All chunks have a `quality_score` annotation
- All scores are in [0, 1]
- `DatasetQualityReport.scored_chunks == total_chunks`
- Score distribution is plausible (mean not 0.0 or 1.0 for a real dataset)

## Threshold application

The quality threshold is applied in the Exporter stage, not the Scorer stage. The Scorer annotates all chunks with their score regardless of threshold. This allows profile-specific thresholds to be applied at export time without re-scoring.

## Failure modes

| Failure | Cause | Resolution |
| --- | --- | --- |
| `GovernanceDenied` | Network scorer endpoint not in policy | Add endpoint to allowed hosts; or use heuristic scorer |
| All scores = 0.0 | Scorer config error or all inputs invalid | Check scorer config; inspect sample chunks |
| All scores = 1.0 | Scorer not penalizing any signal | Check scorer weights; verify threshold signals are active |
| `scored_chunks < total_chunks` | Some chunks raised scoring errors | Check scorer logs for per-chunk errors |

## Evidence produced

- `quality_score` annotation on each chunk
- `DatasetQualityReport` in `DatasetManifest.quality_summary`
- Policy decision records (if scorer uses I/O)
