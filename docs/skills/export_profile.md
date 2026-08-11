# Skill: export_profile

## Purpose

Apply an export profile to a completed `DatasetManifest` to produce a `DatasetBuild` artifact in the target format.

## When to use

- After manifest generation, as the final pipeline stage
- When re-exporting an existing manifest with a different profile (without re-running the full pipeline)
- When testing a new profile config against an existing build

## Inputs

| Input | Type | Description |
| --- | --- | --- |
| `manifest` | `DatasetManifest` | Completed manifest from the ManifestGenerator stage |
| `chunks` | `Iterable[DatasetChunk]` | Scored chunks (loaded from manifest if re-exporting) |
| `profile_id` | string | Export profile config ID |
| `output_path` | string | Output directory for the artifact |
| `version` | string | Semver version for the `DatasetBuild` |
| `context` | `BuildContext` | Pipeline context (for governance) |

## Preconditions

- Manifest exists and is valid
- Profile config exists in `configs/profiles/<profile_id>.yaml`
- Output directory is writable (governance-evaluated before write)
- No chunks with `license_status=incompatible` are present in the input

## Execution steps

1. Load export profile config.
2. Validate profile against manifest:
   - Check `license_requirements` compatibility with manifest's `license_summary`
   - Verify `field_mapping` references valid canonical fields
3. Filter chunks:
   a. Exclude chunks with `quality_score < profile.min_quality_score`
   b. Exclude chunks with `license_status != compatible` (safety check; should already be excluded)
   c. Apply profile `filters` (content type, token count, required annotations)
4. Apply field mapping to each chunk.
5. Evaluate `WRITE` (or `PUBLISH`) governance.
6. Stream-write the export artifact in the profile's `format`.
7. Compute artifact SHA-256 hash.
8. Construct and return `DatasetBuild` and `ExportArtifactRecord`.

## Outputs

| Output | Type | Description |
| --- | --- | --- |
| `build` | `DatasetBuild` | Versioned, releasable build artifact |
| `artifact_record` | `ExportArtifactRecord` | Path, hash, record count |
| `artifact_path` | string | Path to the written artifact file |

## Filtering log

All exclusions during export are logged:

```python
{
    "below_quality_threshold": 1500,
    "license_incompatible": 0,      # should always be 0 (already excluded)
    "missing_required_annotation": 22,
    "below_min_token_count": 8,
    "above_max_token_count": 3,
    "content_type_excluded": 0,
}
```

This log is included in `DatasetBuild.export_summary`.

## Re-exporting without re-running the pipeline

```bash
rif-dataset export \
  --manifest <manifest_id> \
  --profile my-sft-v2 \
  --output /data/builds/ \
  --version 1.1.0
```

The exporter reloads the chunks from the existing manifest. The new export produces a new `DatasetBuild` with a new ID but references the same `manifest_id`. Both builds are valid; neither supersedes the other.

## Failure modes

| Failure | Cause | Resolution |
| --- | --- | --- |
| `GovernanceDenied` | WRITE/PUBLISH policy denied | Check runtime posture; verify policy allows writes to output path |
| `EmptyExportError` | All chunks excluded by filters | Lower threshold; check filter config; investigate chunk quality |
| `LicenseIncompatibleError` | Profile rejects manifest's composite license | Use a profile with compatible `license_requirements` |
| `FieldMappingError` | Canonical field in mapping not on `DatasetChunk` | Fix `field_mapping` in profile config |

## Evidence produced

- `DatasetBuild` artifact at `output_path`
- `ExportArtifactRecord` in `DatasetManifest.lineage.export_artifacts`
- Policy decision record for WRITE/PUBLISH
