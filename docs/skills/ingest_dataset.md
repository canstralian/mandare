# Skill: ingest_dataset

## Purpose

Load a dataset from a registered source and produce raw `DatasetRecord` objects.

## When to use

- Testing a new registry entry before running the full pipeline
- Inspecting raw source records before normalization
- Diagnosing loader errors on a specific dataset

## Inputs

| Input | Type | Description |
| --- | --- | --- |
| `dataset_id` | string | ID of a registered dataset (`configs/datasets/<id>.yaml`) |
| `limit` | int (optional) | Maximum number of records to load. Default: no limit |
| `split` | string (optional) | Dataset split to load. Overrides registry entry config |

## Preconditions

- RIF Runtime is running (`rif serve`)
- `dataset_id` exists in `configs/datasets/` and is `enabled: true`
- The runtime's current posture permits READ operations to the source
- HuggingFace token is in the environment if source is `source_type: huggingface`

## Execution steps

1. Load the registry entry from `configs/datasets/<dataset_id>.yaml`.
2. Validate the entry (schema, license reference, source ref format).
3. Evaluate `READ` governance for the source.
4. Instantiate the appropriate loader (HuggingFace, local, or URL).
5. Call `loader.load(entry, context)` and collect records up to `limit`.
6. Return records and a `StageReport` with count and lineage metadata.

## Outputs

| Output | Type | Description |
| --- | --- | --- |
| `records` | `list[DatasetRecord]` | Raw records from the source |
| `stage_report` | `StageReport` | Record count, source lineage, duration |
| `source_lineage` | `SourceLineage` | Source ref, version, hash, timestamp |

## Validation

After ingestion, verify:

- `len(records) > 0` (empty dataset is likely a loader error)
- All records have a non-empty `id` and `source_id`
- `source_lineage.hash` is set (required for reproducibility)
- No governance denials in the `stage_report`

## Failure modes

| Failure | Cause | Resolution |
| --- | --- | --- |
| `GovernanceDenied` | READ policy denied for source | Check runtime posture and policy rules |
| `RegistryEntryNotFound` | `dataset_id` not in registry | Verify ID and `enabled: true` |
| `LoaderError` | Source unavailable or format mismatch | Check source availability; verify registry config |
| `RateLimitError` | HF Hub rate limit hit | Retry with backoff; check HF token |

## Evidence produced

- `SourceLineage` record in `LineageCollector`
- Policy decision record in `LineageCollector`
- `StageReport` with timing and counts
