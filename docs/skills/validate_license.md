# Skill: validate_license

## Purpose

Validate the license compatibility of each `DatasetRecord` against a target export profile.

## When to use

- After a new dataset is registered, before committing the registry entry
- Before running the full build to estimate how many records will be excluded
- When the license configuration for a source dataset changes
- During License Governor review of a build manifest

## Inputs

| Input | Type | Description |
| --- | --- | --- |
| `dataset_id` | string | Registered dataset ID |
| `profile_id` | string | Export profile ID to validate against |
| `limit` | int (optional) | Maximum records to validate. Default: no limit |

## Preconditions

- `dataset_id` is registered and enabled
- `profile_id` exists in `configs/profiles/`
- License config for the dataset's `license_id` exists in `configs/licenses/`

## Execution steps

1. Load registry entry and resolve `license_id` → `LicenseConfig`.
2. Load export profile and resolve `license_requirements`.
3. For each record (or up to `limit`):
   a. Evaluate license compatibility using the `LicenseValidator`.
   b. Annotate the record with `license_validation` annotation.
   c. Classify as `compatible`, `incompatible`, or `review_required`.
4. Aggregate results into a `LicenseValidationReport`.

## Outputs

| Output | Type | Description |
| --- | --- | --- |
| `report` | `LicenseValidationReport` | Counts by status, composite tier, attribution requirements |
| `incompatible_examples` | `list[DatasetRecord]` | Sample of incompatible records (for review) |
| `review_required_examples` | `list[DatasetRecord]` | Sample of review_required records |

## LicenseValidationReport

```python
class LicenseValidationReport(BaseModel):
    dataset_id: str
    profile_id: str
    total_records: int
    compatible: int
    incompatible: int
    review_required: int
    unknown: int
    composite_tier: str
    attribution_required: bool
    blocking: bool           # True if incompatible > 0
    review_gate: bool        # True if review_required > 0
```

## Decision gates

- `blocking=True`: the dataset cannot be used with this profile. Resolve by choosing a different profile or seeking a license upgrade from the upstream source.
- `review_gate=True`: human review required before proceeding. Create a `HumanApprovalRecord` for each `review_required` license.
- `compatible=total_records` and no `review_gate`: ready to proceed.

## Failure modes

| Failure | Cause | Resolution |
| --- | --- | --- |
| `LicenseConfigNotFound` | `license_id` not in `configs/licenses/` | Create the license config; route to License Governor |
| All records `review_required` | License tier is `unknown` | Classify the license; update config |
| All records `incompatible` | License tier incompatible with profile | Use a different profile or different source |

## Evidence produced

- `LicenseValidationReport` (standalone, not added to LineageCollector in this skill)
- When run as part of the full pipeline: `TransformationRecord` with exclusion counts
