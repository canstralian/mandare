# Quality Reviewer

## Mission

Own the quality model: what quality means, how it is measured, and how scores gate export.

---

## Responsibilities

- Quality scorer implementations and configuration
- Threshold recommendations per profile and content type
- Quality report interpretation and anomaly detection
- Validation that quality scores correlate with training value
- Review of per-build quality reports before publication approval
- Research on new quality signals and scoring methods

---

## Quality review checklist

For every build submitted for publication:

- [ ] Quality report present in manifest (`quality_summary`)
- [ ] Scorer used is documented in `docs/tools/`
- [ ] Exclusion rate is within expected range for the content type (see `docs/research/QUALITY_BENCHMARKS.md`)
- [ ] Score distribution shape is expected (not bimodal or suspiciously flat)
- [ ] Mean and median scores are above the threshold used
- [ ] No single source contributes >30% of excluded chunks (indicates source-specific quality issue)

If any check fails, investigate before approving publication.

---

## Anomaly detection

### Exclusion rate too high (>50%)

Investigate:
1. Is the content type correctly classified? (Misclassified content scores poorly)
2. Is the chunker producing abnormal chunk sizes?
3. Is the source dataset higher-noise than expected?
4. Is the threshold misconfigured for this content type?

### Exclusion rate too low (<5% for a large general-purpose dataset)

Investigate:
1. Is the scorer running? (Check `scored_chunks == total_chunks`)
2. Is the threshold set correctly in the profile?
3. Is the dataset atypically high-quality (expected for human-curated sources)?

### Score distribution is bimodal

Indicates two distinct populations in the dataset (e.g., high-quality human-written + low-quality auto-generated). Consider:
- Running per-source quality analysis
- Setting a higher threshold to exclude the low-quality population

---

## Scorer governance

Plugin scorers that require network access (perplexity, reward) are governed:

- Review that the scorer config includes a valid `endpoint`
- Verify the endpoint is in the allowed hosts list for the runtime environment
- Confirm the `PUBLISH` or `READ` policy is configured for the endpoint

If the scoring endpoint is not in the policy, the scorer will be governance-denied: the stage raises `GovernanceDenied`, the build halts, and the denial is recorded in the audit trail. There is no automatic fallback. To use the heuristic scorer instead, configure the pipeline with `quality_scorer_id: heuristic_scorer`.

---

## Adding a new scorer

New quality scorers require:

1. A specification section in `docs/specifications/QUALITY_MODEL.md`
2. Implementation under `src/rif_runtime/dataset/quality/`
3. Config file under `configs/quality/`
4. Tests under `tests/dataset/quality/`
5. Documentation in `docs/tools/<id>_scorer.md`
6. Quality Reviewer approval

Scorers that call external services also require governance review.

---

## Research obligations

The Quality Reviewer maintains `docs/research/QUALITY_BENCHMARKS.md` with:

- Score distributions for reference datasets (updated when new datasets are added)
- Threshold recommendations by profile and content type
- Documented correlation (where measured) between heuristic scores and training outcomes
