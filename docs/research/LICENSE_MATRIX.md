# License Compatibility Matrix

## Purpose

Reference matrix for license compatibility across export profiles.

For authoritative decisions on specific datasets, route to the License Governor. This matrix covers the common cases; edge cases require legal review.

## Matrix

| License | Tier | SFT (commercial) | DPO (commercial) | RAG (commercial) | Evaluation | SFT (research) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MIT | permissive | ✅ | ✅ | ✅ | ✅ | ✅ | |
| Apache-2.0 | permissive | ✅ | ✅ | ✅ | ✅ | ✅ | Attribution required in manifest |
| BSD-2-Clause | permissive | ✅ | ✅ | ✅ | ✅ | ✅ | |
| BSD-3-Clause | permissive | ✅ | ✅ | ✅ | ✅ | ✅ | |
| CC0-1.0 | permissive | ✅ | ✅ | ✅ | ✅ | ✅ | No attribution required |
| CC-BY-4.0 | permissive | ✅ | ✅ | ✅ | ✅ | ✅ | Attribution required |
| CC-BY-SA-4.0 | copyleft_weak | ✅ | ✅ | ✅ | ✅ | ✅ | Share-alike; attribution required |
| LGPL-2.1 | copyleft_weak | ✅ | ✅ | ✅ | ✅ | ✅ | |
| CC-BY-NC-4.0 | non_commercial | ❌ | ❌ | ❌ | ❌ | ✅ | NC flag; commercial use prohibited |
| CC-BY-NC-SA-4.0 | non_commercial | ❌ | ❌ | ❌ | ❌ | ✅ | NC + share-alike |
| GPL-2.0 | copyleft_strong | ❌ | ❌ | ❌ | ❌ | ⚠️ | Strong copyleft; review required |
| GPL-3.0 | copyleft_strong | ❌ | ❌ | ❌ | ❌ | ⚠️ | Strong copyleft; review required |
| AGPL-3.0 | copyleft_strong | ❌ | ❌ | ❌ | ❌ | ⚠️ | Network copyleft; review required |
| OpenRAIL | custom | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Use restrictions apply; review per dataset |
| OpenRAIL-M | custom | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | Model-specific use restrictions |
| Proprietary | proprietary | ❌ | ❌ | ❌ | ❌ | ❌ | |
| Unknown | unknown | ❌ | ❌ | ❌ | ❌ | ❌ | Review required |

Legend:
- ✅ Compatible
- ❌ Incompatible
- ⚠️ Review required — route to License Governor

## OpenRAIL notes

OpenRAIL and OpenRAIL-M licenses permit broad use but impose behavioral use restrictions (e.g., must not be used for certain harmful applications). They are not compatible with the simple tier model.

OpenRAIL datasets require a use-restriction annotation in the manifest and a `HumanApprovalRecord` confirming the intended use is permitted. Treat them as `review_required` by default.

## GPT-generated data notes

Datasets generated using GPT-4, GPT-3.5-turbo, or other OpenAI models may be subject to OpenAI's Terms of Service, which prohibit using outputs to train models that compete with OpenAI's products.

This is a contractual restriction, not a copyright license. It cannot be captured in the license tier model. Datasets with GPT-generated content must be flagged manually with a `contractual_restriction` annotation and routed to the License Governor.

## Composite license rules

When combining datasets:
1. The composite license is the most restrictive tier across all sources.
2. If any source is `non_commercial`, the composite is `non_commercial`.
3. If any source is `copyleft_strong`, the composite is `copyleft_strong`.
4. If any source is `proprietary`, the build is blocked.
5. If any source is `unknown`, the build is blocked unless all unknown sources are covered by `HumanApprovalRecord`.

## Attribution tracking

Datasets with `attribution_required: true` must have their attribution recorded in the `DatasetManifest.license_summary.attributions` field:

```python
class LicenseSummary(BaseModel):
    compatible: int
    incompatible: int
    review_required: int
    unknown: int
    composite_tier: str
    attributions: list[Attribution]

class Attribution(BaseModel):
    source_id: str
    license_id: str
    attribution_text: str          # from configs/licenses/<id>.yaml
```

The `attribution_text` is the standard attribution string for the license (e.g., the Apache-2.0 notice template).
