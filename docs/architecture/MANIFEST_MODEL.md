# Manifest Model

## Purpose

The `DatasetManifest` is the root artifact of every build. It is the single source of truth for reproducibility, lineage, and governance audit.

## Immutability

A manifest is finalized once and never modified. The `ManifestGenerator` produces it at the end of the pipeline run. Subsequent pipeline stages (export) read from the manifest; they do not write to it.

If a re-run is required, a new manifest with a new ID is produced. Old manifests are retained.

## Manifest ID

Manifest IDs are UUIDs (v4). They are not derived from content. Two builds of the same dataset with the same config produce different manifest IDs.

Content-addressable reproducibility is tracked via `DatasetBuild.artifact_hash`, not via the manifest ID.

## Reproducibility flag

`DatasetManifest.reproducible` is `True` when:

- All source datasets have a pinned `source_version` (non-null)
- All source fetches have a recorded `hash`
- All config files referenced in `pipeline_config` are pinned to a git commit
- No plugin with `type: plugin` has a null `plugin_version`

A manifest with `reproducible=False` may still be valid. It records that at least one input is not fully pinned.

## Manifest as a build receipt

The manifest records everything that happened during a build:

```
DatasetManifest
  id: uuid
  version: "1.0.0"
  created_at: "2026-08-05T12:00:00Z"
  reproducible: true

  sources:
    - id: code-alpaca
      source_ref: sahil2801/CodeAlpaca-20k
      source_version: abc123
      fetch_timestamp: "..."
      record_count: 20022
      hash: sha256:...

  pipeline_config:
    loader_id: huggingface_loader
    quality_scorer_id: heuristic_scorer
    chunker_map: {...}
    export_profile_id: sft
    ...

  stage_reports:
    loader:
      input_count: 0
      output_count: 20022
      duration_ms: 4512
    license_validator:
      input_count: 20022
      output_count: 20022
      excluded_count: 0
    normalizer: {...}
    ...

  policy_decisions:
    - actor: "pipeline.loader"
      action: "READ"
      target: "hf://sahil2801/CodeAlpaca-20k"
      decision: "allow"
      rule_id: null
      timestamp: "..."
    - actor: "pipeline.exporter"
      action: "WRITE"
      target: "/data/builds/sft-v1.0.0.jsonl"
      decision: "allow"
      rule_id: null
      timestamp: "..."

  record_count: 19500
  chunk_count: 31200
  license_summary:
    compatible: 19500
    incompatible: 0
    review_required: 0
    unknown: 522

  quality_summary:
    total_chunks: 31200
    scored_chunks: 31200
    excluded_chunks: 4680
    mean_score: 0.71
    threshold_used: 0.60

  lineage:
    sources: [...]
    transformations: [...]
    policy_decisions: [...]
    export_artifacts: [...]
```

## Manifest storage

Manifests are written to `data/manifests/<manifest_id>.json` by the `ManifestGenerator`.

The `data/manifests/` directory is gitignored (runtime state). A build's manifest must be included in the `DatasetBuild` artifact package if the build is to be shared or reproduced.

## Querying manifests

The audit API (`GET /v1/audit`) surfaces policy decisions from all builds.

A future `GET /v1/manifests` endpoint will allow querying manifests by ID, version, source, or date range.

## Manifest validation

A manifest is valid if:

1. All required fields are present and well-typed.
2. `record_count` matches the sum of `stage_reports.loader.output_count` minus total exclusions.
3. `chunk_count` matches the sum of all chunks produced by the Chunking stage minus exclusions.
4. All `policy_decisions` recorded in `lineage.policy_decisions` appear in `stage_reports`.
5. `DatasetBuild.manifest_id` references a manifest that exists on disk.

The `rif-dataset validate-manifest <manifest_id>` command runs these checks.
