# License Policy Specification

## Purpose

Define how the Dataset Foundry validates source dataset licenses and enforces compatibility with export profiles.

## Design principle

License validation is a gate, not a filter. An incompatible license stops the record from appearing in any export. It does not stop the build; it stops that record.

License interpretation is not automated. The system classifies licenses into compatibility tiers based on configuration. Edge cases require human legal review.

## License tiers

| Tier | Meaning | Export permitted |
| --- | --- | --- |
| `permissive` | MIT, Apache-2.0, BSD, CC-BY | Yes, all profiles |
| `copyleft_weak` | LGPL, CC-BY-SA | Yes, with attribution requirement in manifest |
| `copyleft_strong` | GPL, AGPL | No (incompatible with closed model training) |
| `non_commercial` | CC-BY-NC, custom NC | No by default; yes if profile is explicitly `non_commercial_permitted: true` |
| `proprietary` | Custom, restricted | No |
| `unknown` | License not identified | Excluded by default; review_required annotation |
| `research_only` | Custom research use | Yes if profile is `research_only_permitted: true` |

## License configuration

Each dataset registry entry references a license config file:

```yaml
# configs/licenses/apache-2.0.yaml
id: apache-2.0
spdx_id: Apache-2.0
tier: permissive
attribution_required: true
share_alike_required: false
commercial_use_permitted: true
modification_permitted: true
sublicense_permitted: true
notes: ""
```

Custom and proprietary licenses require a manually-authored config file with `tier: proprietary` unless otherwise determined by legal review.

## Compatibility rules

Compatibility is evaluated per record against the export profile's `license_requirements`:

```yaml
# configs/profiles/sft.yaml
license_requirements:
  permitted_tiers:
    - permissive
    - copyleft_weak
  non_commercial_permitted: false
  research_only_permitted: false
  require_attribution_in_manifest: true
```

A record's license is compatible if its tier is in `permitted_tiers` AND all enabled requirements are satisfied.

## Validation result states

| State | Condition |
| --- | --- |
| `compatible` | Tier is permitted and all requirements satisfied |
| `incompatible` | Tier is not permitted or a required condition is violated |
| `review_required` | Tier is `unknown` or license config has `requires_review: true` |

## Annotation

The license validation stage annotates each `DatasetRecord` with:

```python
Annotation(
    key="license_validation",
    value={
        "license_id": "apache-2.0",
        "tier": "permissive",
        "status": "compatible",
        "profile_id": "sft",
        "checked_at": "2026-08-05T00:00:00Z",
    },
    source="license_validator",
)
```

## Enforcement

- Records with `license_status=incompatible` are excluded from all export artifacts and counted in the `TransformationRecord.exclusion_reasons["license_incompatible"]` tally.
- Records with `license_status=review_required` are excluded unless the export profile has `permit_review_required: true` AND the manifest includes a `HumanApprovalRecord` for that license.
- Records with `license_status=unknown` are treated as `review_required`.

## HumanApprovalRecord

When a profile permits `review_required` records, the manifest must include:

```python
class HumanApprovalRecord(BaseModel):
    license_id: str
    approved_by: str              # identity of the human reviewer
    approved_at: datetime
    scope: str                    # what is approved (e.g., "training use, non-commercial")
    notes: str
```

Absent a `HumanApprovalRecord`, `review_required` records are excluded regardless of profile settings.

## License composition

When combining multiple source datasets, the composite license is the most restrictive tier present across all sources.

The manifest records:

- All unique source licenses
- The composite license tier
- Any attribution requirements inherited from sources

A build fails if the composite license tier is incompatible with the export profile.

## Updating license configurations

License config files are checked into git under `configs/licenses/`. Changes to license configs require:

1. A PR with rationale
2. Review by the License Governor agent
3. Human approval if the change affects any `non_commercial`, `research_only`, or `proprietary` tier entries

The License Governor agent does not have authority to approve license tier changes unilaterally. It may recommend; a human must approve.
