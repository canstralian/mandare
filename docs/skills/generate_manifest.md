# Skill: generate_manifest

## Purpose

Produce the immutable `DatasetManifest` from the accumulated pipeline state.

## When to use

- At the end of the pipeline, after all stages are complete
- When reconstructing a manifest from a partially recovered build state
- When verifying that a manifest is consistent with the pipeline's `LineageCollector` state

## Inputs

| Input | Type | Description |
| --- | --- | --- |
| `context` | `BuildContext` | Pipeline context with `lineage` and `pipeline_config` |
| `chunks` | `list[DatasetChunk]` | Final scored chunks (post-quality-scoring) |
| `version` | string | Semver version for this build |
| `manifest_path` | string (optional) | Output path for the manifest file. Default: `data/manifests/<id>.json` |

## Preconditions

- All pipeline stages have completed
- `context.lineage` has been populated by all stages
- All source fetches have a recorded hash in `SourceLineage`
- RIF Runtime is running (for WRITE governance evaluation)

## Execution steps

1. Finalize the `LineageCollector` (no further writes permitted after this).
2. Compute aggregate statistics:
   - `record_count`: total records from the Loader stage minus all exclusions
   - `chunk_count`: total chunks from the Chunking stage minus quality exclusions
   - `license_summary`: counts by status, composite tier, attributions
   - `quality_summary`: score distribution, mean, median
3. Determine `reproducible` flag:
   - True if all sources have pinned `source_version` and recorded `hash`
   - True if all plugin configs have non-null `plugin_version`
4. Construct the `DatasetManifest`.
5. Evaluate `WRITE` governance for `manifest_path`.
6. Serialize the manifest to `manifest_path`.
7. Return the manifest.

## Outputs

| Output | Type | Description |
| --- | --- | --- |
| `manifest` | `DatasetManifest` | Immutable build manifest |
| `manifest_path` | string | Path where the manifest was written |

## Manifest invariants

The generated manifest must satisfy:

- `manifest.record_count` == `loader.output_count` - sum of all stage exclusion counts
- `manifest.chunk_count` == `chunker.output_count` - `scorer_excluded_count` - `below_quality_threshold_count`
- `manifest.reproducible == True` iff all reproducibility conditions are met
- `manifest.lineage.policy_decisions` contains an entry for every governed operation

## Validation

Run after generation:

```bash
rif-dataset validate-manifest <manifest_id>
```

Must pass before the Exporter stage proceeds.

## Failure modes

| Failure | Cause | Resolution |
| --- | --- | --- |
| `GovernanceDenied` | WRITE policy denied for manifest path | Check runtime posture; verify output directory policy |
| `ManifestValidationError` | Invariants violated | Investigate stage report inconsistencies |
| `LineageCollectorFinalizedError` | Stage attempted to write to lineage after finalization | Pipeline stage ordering violated; fix stage sequence |

## Evidence produced

- `DatasetManifest` file at `manifest_path`
- Policy decision record for the WRITE operation
