# Dataset Foundry Specification

## Purpose

Define the contracts, boundaries, and invariants for the Dataset Foundry platform.

This specification is the authoritative reference for all implementation decisions. When implementation and specification conflict, update the specification first and get review, then update the implementation.

## System boundary

The Dataset Foundry is a pipeline that:

1. Accepts a dataset registry entry as input
2. Produces a versioned, reproducible DatasetBuild as output
3. Records full lineage between input and output
4. Routes all effectful operations through RIF Runtime governance

The pipeline does not:

- Train models
- Evaluate models
- Serve inference
- Make autonomous publication decisions

## Pipeline contract

```text
Registry Entry
      │
      ▼
Loader (effect: READ)
      │
      ▼
License Validation (non-governed: local config only)
      │
      ▼
Normalization
      │
      ▼
Classification
      │
      ▼
Deduplication
      │
      ▼
Chunking
      │
      ▼
Quality Scoring
      │
      ▼
Manifest Generation
      │
      ▼
Export Profile Application (effect: WRITE)
      │
      ▼
DatasetBuild (immutable artifact)
```

Every stage transition produces an immutable intermediate artifact.

Failed stages do not proceed. Partial builds are not releasable.

## Stage contracts

### Loader

- Input: `DatasetRegistryEntry`
- Output: `Iterable[DatasetRecord]`
- Effect: READ (network or filesystem)
- Governed: yes — policy evaluation before fetch
- Produces: source lineage metadata

### License Validation

- Input: `DatasetRecord`, license configuration
- Output: `DatasetRecord` with `license_status` annotation
- Effect: none (reads config, no network)
- Governed: no (read-only, config-driven)
- Produces: license compatibility report

Validation result is `compatible`, `incompatible`, or `review_required`.

Records annotated `incompatible` are excluded from all export profiles.
Records annotated `review_required` are excluded unless the profile explicitly permits them with human approval metadata.

### Normalization

- Input: `Iterable[DatasetRecord]`
- Output: `Iterable[DatasetRecord]` in canonical schema
- Effect: none
- Governed: no
- Produces: normalization report (field mapping, null rates, schema coverage)

Normalization must not discard source data. Fields not mappable to canonical schema are preserved in `DatasetRecord.extra`.

### Classification

- Input: `Iterable[DatasetRecord]`
- Output: `Iterable[DatasetRecord]` with `content_type` annotation
- Effect: none
- Governed: no
- Produces: classification distribution report

Content types: `code`, `conversation`, `document`, `trace`, `structured`, `unknown`.

Classification is config-driven. Classifiers are not models; they are rule-based heuristics unless a classification plugin is configured.

### Deduplication

- Input: `Iterable[DatasetRecord]`
- Output: `Iterable[DatasetRecord]` with duplicates removed
- Effect: none
- Governed: no
- Produces: deduplication report (removed count, method, similarity threshold)

Exact deduplication (hash-based) is the default. Near-duplicate deduplication requires a plugin.

### Chunking

- Input: `Iterable[DatasetRecord]`
- Output: `Iterable[DatasetChunk]`
- Effect: none
- Governed: no
- Produces: chunking report (chunk count, size distribution, strategy used)

Chunker selection is config-driven by `content_type`. Each content type maps to exactly one chunker in the pipeline configuration. Multiple chunkers may be registered; only one is active per content type per build.

### Quality Scoring

- Input: `Iterable[DatasetChunk]`
- Output: `Iterable[DatasetChunk]` with quality annotations
- Effect: none (unless scoring plugin requires network)
- Governed: yes if effect required
- Produces: quality distribution report

Quality score is a float in [0, 1]. Chunks below the profile's `min_quality_score` threshold are excluded from export.

### Manifest Generation

- Input: All stage outputs and reports
- Output: `DatasetManifest` (immutable)
- Effect: WRITE (manifest file)
- Governed: yes
- Produces: `DatasetManifest`

The manifest records every source, every configuration value, every policy decision, and every stage output. It is the root artifact for reproducibility.

### Export Profile Application

- Input: `DatasetManifest`, `DatasetExportProfile`
- Output: export artifact (JSONL, Parquet, Arrow, or HF dataset)
- Effect: WRITE (filesystem or HF Hub push)
- Governed: yes — policy evaluation before every write
- Produces: `DatasetBuild`

## Invariants

1. No record with `license_status=incompatible` appears in any export artifact.
2. Every export artifact has a corresponding `DatasetManifest` with full lineage.
3. Every effectful operation has a recorded policy decision.
4. A `DatasetBuild` is reproducible if its `DatasetManifest` is available and sources are accessible.
5. Stage outputs are immutable. A stage may not modify its own input.
6. Configuration drives behavior. Pipeline code does not branch on dataset identity or content.

## Error handling

Stage failures halt the build and record a `BuildFailureRecord` with:

- stage name
- error type and message
- partial lineage up to the point of failure
- policy decisions made before the failure

Partial builds are never emitted as `DatasetBuild` artifacts. They are retained as `DatasetBuildAttempt` records for forensic review.

## Versioning

`DatasetBuild` versions follow `<major>.<minor>.<patch>`:

- `patch`: configuration changes, re-runs with same source version
- `minor`: source dataset updated, new chunker or quality model, filter changes
- `major`: schema change, license policy change, incompatible format change
