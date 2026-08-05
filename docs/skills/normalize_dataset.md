# Skill: normalize_dataset

## Purpose

Transform raw `DatasetRecord` objects from source-specific field names to the canonical schema.

## When to use

- After ingestion, before classification or chunking
- When inspecting whether a source dataset maps cleanly to the canonical schema
- When diagnosing high `extra` field rates (fields not mappable to canonical schema)

## Inputs

| Input | Type | Description |
| --- | --- | --- |
| `records` | `Iterable[DatasetRecord]` | Raw records from the Loader stage |
| `normalizer_id` | string | Normalizer config ID from `configs/` |

## Preconditions

- Records are in raw form (straight from the Loader, not yet normalized)
- Normalizer config exists and is valid

## Execution steps

1. Load normalizer config for `normalizer_id`.
2. For each record:
   a. Apply field mapping from source field names to canonical field names.
   b. Coerce field types to canonical types (e.g., list of strings to `messages` list).
   c. Preserve unmapped fields in `record.extra`.
   d. Validate the result against the `DatasetRecord` schema.
3. Collect normalization stats: field coverage rates, null rates, records with non-empty `extra`.
4. Return normalized records and a `NormalizationReport`.

## Outputs

| Output | Type | Description |
| --- | --- | --- |
| `records` | `Iterable[DatasetRecord]` | Normalized records in canonical schema |
| `report` | `NormalizationReport` | Field coverage, null rates, extra field rates |

## Normalization rules

- Normalization must not discard source data. Unmapped fields go to `record.extra`.
- Normalization must not modify `record.id` or `record.source_index`.
- Type coercion is allowed; semantic interpretation is not.
- If a record fails validation after normalization, it is excluded with reason `"normalization_failed"` and counted in the report.

## Validation

After normalization:

- `record.text` is set OR `record.messages` is set (not both null)
- `record.source_id` matches the registry entry ID
- No required fields are null

## Failure modes

| Failure | Cause | Resolution |
| --- | --- | --- |
| High `extra` field rate | Source schema differs from canonical | Update normalizer field mapping config |
| High `normalization_failed` count | Source has non-standard types | Extend normalizer with type coercion rules |
| All records have null `text` and `messages` | Primary field not identified | Check field mapping config |

## Evidence produced

- `TransformationRecord` in `LineageCollector` with input/output counts and exclusion reasons
