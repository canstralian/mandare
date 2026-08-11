# Quality Model Specification

## Purpose

Define the quality scoring stage: what quality means, how it is measured, and how scores gate export.

## What quality means

A quality score is a signal about the fitness of a chunk for its intended training objective. It is not a universal ground truth. The quality model is profile-aware: a chunk that scores well for SFT may score poorly for DPO.

The score is a float in [0, 1]. Higher is better.

## Built-in scorers

### heuristic_scorer

Rule-based, zero-latency, no external dependencies.

Evaluates:

| Signal | Weight |
| --- | --- |
| Character count within range | 0.15 |
| Token count within range | 0.15 |
| Repetition ratio (repeated n-grams) | 0.20 |
| Compression ratio (as proxy for information density) | 0.20 |
| Language detection confidence (if configured) | 0.10 |
| Well-formedness (valid JSON for structured, parses cleanly for code) | 0.20 |

Weights are configurable. Signals not applicable to a content type are excluded and remaining weights are renormalized.

Config:

```yaml
scorer_id: heuristic_scorer
weights:
  char_count: 0.15
  token_count: 0.15
  repetition: 0.20
  compression: 0.20
  language_confidence: 0.10
  well_formedness: 0.20
min_char_count: 64
max_char_count: 16000
min_token_count: 16
max_token_count: 4096
repetition_ngram_size: 4
repetition_threshold: 0.3         # fraction of duplicate ngrams before penalizing
compression_tool: zlib
language_detection: false
```

### perplexity_scorer

Uses a small reference language model to score perplexity. Lower perplexity = more natural, coherent text = higher quality score.

The perplexity scorer is a plugin. It requires network access (to a local or remote inference endpoint) and is governed.

Config:

```yaml
scorer_id: perplexity_scorer
type: plugin
endpoint: http://localhost:8080/v1/perplexity   # governed READ
model_id: gpt2
max_tokens: 2048
target_perplexity_range: [10, 80]   # normalized to [0,1] within this range
```

### reward_scorer

Uses a reward model to score quality for alignment datasets (DPO).

Plugin. Requires network access and governance.

Config:

```yaml
scorer_id: reward_scorer
type: plugin
endpoint: http://localhost:8080/v1/reward
model_id: reward-model-v1
```

## Composite scoring

Multiple scorers may be combined with a weighted average:

```yaml
scorer_id: composite_scorer
scorers:
  - id: heuristic_scorer
    weight: 0.6
  - id: perplexity_scorer
    weight: 0.4
```

## Quality threshold enforcement

The export profile sets the minimum quality score:

```yaml
# configs/profiles/sft.yaml
min_quality_score: 0.6
```

Chunks below the threshold are excluded from the export artifact. They are counted in `TransformationRecord.exclusion_reasons["below_quality_threshold"]`.

## QualityReport

Every build produces a `DatasetQualityReport`:

```python
DatasetQualityReport(
    manifest_id=...,
    total_chunks=10000,
    scored_chunks=10000,
    excluded_chunks=1500,
    score_distribution={
        "p10": 0.42,
        "p25": 0.58,
        "p50": 0.71,
        "p75": 0.83,
        "p90": 0.91,
    },
    mean_score=0.69,
    median_score=0.71,
    threshold_used=0.60,
    scorer_id="heuristic_scorer",
)
```

The quality report is embedded in the `DatasetManifest`.

## Score annotation

Each `DatasetChunk` is annotated with its quality score and scorer:

```python
Annotation(
    key="quality_score",
    value={"score": 0.74, "scorer_id": "heuristic_scorer"},
    source="quality_scorer",
)
```

## Score stability

The heuristic scorer is deterministic. Given the same chunk text and config, it produces the same score.

Plugin scorers (perplexity, reward) may be non-deterministic due to model sampling. When reproducibility is required, use the heuristic scorer or a plugin scorer with `temperature=0` and a pinned model version.

## Extending the quality model

To add a new scorer:

1. Implement the `Scorer` protocol.
2. Add a config file under `configs/quality/<id>.yaml`.
3. If the scorer requires I/O, route all requests through `BuildContext.governance`.
4. Document the scorer in `docs/tools/<id>_scorer.md`.
5. Add tests under `tests/dataset/quality/test_<id>.py`.
