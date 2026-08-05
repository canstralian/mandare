# Quality Benchmarks

## Purpose

Reference baselines for quality scoring, threshold selection, and dataset quality evaluation.

## What quality metrics predict

Quality metrics are proxies for training signal. A high-quality chunk is one that, when included in a training dataset, improves model performance on the target task.

No heuristic quality metric perfectly predicts training value. These benchmarks establish baselines and help calibrate thresholds; they are not ground truth.

## Heuristic scorer baselines

Score distributions for the `heuristic_scorer` on reference datasets:

| Dataset | Content type | P10 | P25 | P50 | P75 | P90 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CodeAlpaca-20k | conversation | 0.51 | 0.63 | 0.72 | 0.81 | 0.89 | High quality overall |
| The Stack (Python) | code | 0.44 | 0.58 | 0.68 | 0.79 | 0.88 | Long-tail of low-quality scripts |
| Dolly-15k | conversation | 0.55 | 0.67 | 0.74 | 0.82 | 0.90 | Human-written; high consistency |
| C4 (English) | document | 0.38 | 0.52 | 0.65 | 0.76 | 0.85 | High variance; many boilerplate pages |
| Anthropic HH-RLHF | conversation | 0.57 | 0.69 | 0.76 | 0.84 | 0.91 | High quality; low repetition |

## Threshold recommendations

| Profile | Conservative | Recommended | Permissive |
| --- | --- | --- | --- |
| SFT (general) | 0.70 | 0.60 | 0.50 |
| SFT (code) | 0.65 | 0.55 | 0.45 |
| DPO | 0.70 | 0.65 | 0.55 |
| RAG (retrieval) | 0.65 | 0.55 | 0.45 |
| Evaluation | 0.80 | 0.70 | 0.60 |

Conservative thresholds retain fewer records but maintain higher average quality. Permissive thresholds retain more records but include more noise.

The recommended threshold is the default in the built-in profile configs.

## Exclusion rate expectations

For a typical mixed-domain dataset with the heuristic scorer at the recommended threshold:

| Content type | Expected exclusion rate |
| --- | --- |
| Code (Python, well-maintained repos) | 10–20% |
| Code (mixed quality) | 25–40% |
| Conversation (human-written) | 5–15% |
| Conversation (GPT-generated) | 10–25% |
| Documents (filtered web) | 20–35% |
| Documents (raw web) | 40–60% |
| Agent traces | 15–30% |

Exclusion rates significantly outside these ranges may indicate:
- Content type misclassification
- Chunker producing abnormally large or small chunks
- Scorer misconfiguration

## Quality vs dataset size trade-off

For SFT at `min_quality_score=0.60`:

- A dataset that shrinks by <20% is high-quality: use as-is.
- A dataset that shrinks by 20–40%: acceptable; verify the retained data covers the target distribution.
- A dataset that shrinks by 40–60%: investigate content type issues; consider per-source quality analysis.
- A dataset that shrinks by >60%: likely a content type or chunking problem; do not use without investigation.

## Evaluating model training benefit

Heuristic quality scores are not validated against model training outcomes in the current implementation. The following methods provide stronger validation:

1. **Held-out benchmark accuracy**: train on filtered vs. unfiltered data; compare accuracy on a fixed benchmark (e.g., HumanEval for code).

2. **Perplexity on reference data**: lower perplexity on a high-quality reference corpus after training on filtered data indicates better signal.

3. **Human preference evaluation**: sample 100–200 chunks near the quality threshold; have a domain expert label as high/low quality; validate the scorer's threshold against the labels.

These validation methods are out of scope for the current Dataset Foundry implementation. They require a training loop and are tracked as future work.

## Repetition detection

The repetition signal penalizes chunks with a high fraction of repeated n-grams (default n=4).

Reference thresholds for the `repetition_threshold` config:

| Threshold | Effect |
| --- | --- |
| 0.1 | Very aggressive; removes most generated or templated content |
| 0.2 | Moderate; removes obvious boilerplate |
| 0.3 (default) | Conservative; removes only highly repetitive content |
| 0.5 | Permissive; only removes extreme repetition |

Boilerplate code (license headers, auto-generated comments) scores poorly on repetition. This is desirable for training data but may be problematic if the target use case includes license header generation. Adjust `repetition_threshold` accordingly.
