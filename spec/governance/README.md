# spec/governance

Governance contracts for RIF Runtime.

| File | Role |
| --- | --- |
| [`GOVERNANCE_AS_CODE.md`](./GOVERNANCE_AS_CODE.md) | **v1.0 GaC freeze** — DSL, evaluation order, conflicts, examples, tests, explanations |
| [`policy_pack.schema.json`](./policy_pack.schema.json) | Policy pack schema (`rif.runtime.policy/v1`) |
| [`policy_explanation.schema.json`](./policy_explanation.schema.json) | Explainable decision output |
| [`posture_decision.schema.json`](./posture_decision.schema.json) | Legacy Familiar posture-decision seed |

Runtime today: `src/rif_runtime/policy.py` (partial). Target: pure evaluator conforming to GaC SPEC, emitting `governance.evaluated`.
