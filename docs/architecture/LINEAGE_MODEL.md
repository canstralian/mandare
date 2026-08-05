# Lineage Model

## Purpose

Every artifact produced by the Dataset Foundry carries a provenance chain that answers: where did this data come from, what happened to it, and who authorized each step?

## Design

Lineage is accumulated by the `LineageCollector` throughout the pipeline run and finalized in the `DatasetManifest`. It is not a separate system; it is part of the manifest model.

The lineage model has four record types:

```
DatasetLineage
  │
  ├── sources[]         → SourceLineage
  ├── transformations[] → TransformationRecord
  ├── policy_decisions[]→ PolicyDecisionRecord
  └── export_artifacts[]→ ExportArtifactRecord
```

## SourceLineage

Records the provenance of each ingested source.

```python
class SourceLineage(BaseModel):
    registry_entry_id: str       # configs/datasets/<id>.yaml
    source_ref: str              # HF dataset id, path, or URL
    source_version: str | None   # pinned revision, or null if not pinned
    fetch_timestamp: datetime    # when the source was fetched
    record_count: int            # number of records loaded
    hash: str                    # SHA-256 of the fetched content
```

The `hash` is computed over the raw fetched bytes before any transformation. It is the anchor for reproducibility verification.

## TransformationRecord

Records what each pipeline stage did.

```python
class TransformationRecord(BaseModel):
    stage: str                           # "normalization" | "chunking" | ...
    config_ref: str                      # path and content hash of config used
    input_count: int
    output_count: int
    excluded_count: int
    exclusion_reasons: dict[str, int]    # reason -> count
    duration_ms: int
    timestamp: datetime
```

`exclusion_reasons` maps reason strings to counts:

```python
{
    "license_incompatible": 0,
    "below_quality_threshold": 1500,
    "exact_duplicate": 300,
    "below_min_tokens": 22,
}
```

## PolicyDecisionRecord

Records every governance evaluation.

```python
class PolicyDecisionRecord(BaseModel):
    actor: str           # "pipeline.<stage_id>"
    action: str          # "READ" | "WRITE" | "PUBLISH"
    target: str          # resource reference
    decision: str        # "allow" | "deny"
    reason: str | None   # populated on deny
    rule_id: str | None  # policy rule that matched, if any
    posture: str         # runtime posture at decision time
    timestamp: datetime
```

## ExportArtifactRecord

Records each export artifact produced.

```python
class ExportArtifactRecord(BaseModel):
    profile_id: str
    format: str          # "jsonl" | "parquet" | "arrow" | "huggingface"
    artifact_path: str
    artifact_hash: str   # SHA-256 of the artifact file
    record_count: int
    created_at: datetime
```

## Lineage depth

The lineage model is one level deep: source → transformations → export. It does not recursively trace the lineage of a dataset that was itself built by the Dataset Foundry.

If a derived dataset (one built by the Foundry) is used as a source for another build, the new build's `SourceLineage` records the `artifact_hash` of the source build's export artifact. A consumer who wants the full transitive lineage must resolve the chain manually using the source build's manifest.

## Lineage integrity

The `DatasetManifest` is content-addressable via its own hash (SHA-256 of the JSON-serialized manifest). This hash is recorded in the `DatasetBuild.manifest_hash` field.

Lineage integrity is verified by:

1. Recomputing the manifest hash and comparing to `DatasetBuild.manifest_hash`.
2. Verifying each `SourceLineage.hash` against the current content of the source (requires re-fetching or having the raw data available).
3. Verifying each `ExportArtifactRecord.artifact_hash` against the artifact on disk.

The `rif-dataset verify-lineage <build_id>` command performs these checks.

## Lineage and replay

The `ReplayEngine` (from RIF Runtime) can reconstruct the governance graph and posture history from `data/decisions.jsonl`.

The `DatasetManifest.policy_decisions` provides the dataset-build-specific view of the same data. The two sources should agree; if they diverge, the `decisions.jsonl` is authoritative (it is the append-only log; the manifest is a derived summary).
