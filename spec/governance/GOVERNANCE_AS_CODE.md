# Governance-as-Code for RIF Runtime v1.0

**Status:** Frozen design (Track B).  
**Implements:** executable policy evaluation over a declared input context.  
**Emits into:** `governance.evaluated` ([`spec/events/SPEC.md`](../events/SPEC.md)).  
**Replay:** decisions must be reconstructable by [`spec/replay/SPEC.md`](../replay/SPEC.md).

## Assumptions

| Assumption | Operational impact |
| --- | --- |
| Evaluation is a **pure function** of `PolicyInput` + compiled policy pack + frozen snapshots | No LLM / no hidden process memory in the decision path |
| Operating mode, budget, capability manifest, intent, evidence availability, and risk score are **explicit inputs** | Missing fields fail closed or use declared defaults — never silent omission |
| v1 DSL is **data** (YAML/JSON), not a Turing-complete language | Deterministic, reviewable, CI-testable as code |
| Today’s `PolicyEngine` is a **partial implementation** of this contract | Wildcards skipped + `default.allow` must be replaced for honest deny-by-default |

## Goal

Convert the conceptual governance layer into **executable, explainable, auditable** policy evaluation suitable for governance-as-code (GaC) in CI and at runtime.

---

## 1. Policy DSL (minimal)

### 1.1 Pack shape

```yaml
# policies/runtime.v1.yaml
schema_version: rif.runtime.policy/v1
pack_id: pack_runtime_default
description: RIF Runtime v1.0 baseline governance pack

defaults:
  effect: deny                    # fail closed when no rule matches
  reason_code: DEFAULT_DENY

# Optional: named predicates referenced by rules (v1: built-ins only)
builtins_allowed:
  - posture_at_least
  - posture_is
  - mode_in
  - budget_remaining_gte
  - capability_declared
  - evidence_present
  - risk_lte
  - host_matches
  - action_is
  - action_prefix
  - intent_hash_eq

rules:
  - id: posture_locked
    description: Locked posture denies all capability use
    effect: deny
    reason_code: POSTURE_LOCKED
    when:
      all:
        - { posture_is: locked }
    # no capability filter → applies to every request

  - id: allow_known_model_hosts
    effect: allow
    reason_code: NETWORK_HOST_ALLOWED
    priority: 100
    when:
      all:
        - { action_is: http.request }
        - { host_matches: ["api.anthropic.com", "api.openai.com"] }
        - { mode_in: [governed_execute, read_only] }
        - { risk_lte: 0.7 }
        - { budget_remaining_gte: { requests: 1 } }

  - id: require_evidence_for_destructive
    effect: deny
    reason_code: EVIDENCE_REQUIRED
    priority: 50
    when:
      all:
        - { capability_declared: { id: "mcp.metasploit", risk_class: destructive } }
        - { not: { evidence_present: ["approval_token"] } }

  - id: deny_unknown
    effect: deny
    reason_code: DEFAULT_DENY
    priority: 0
    when:
      all: []    # matches everything; lowest priority catch-all
```

### 1.2 JSON Schema (normative summary)

Full file: [`policy_pack.schema.json`](./policy_pack.schema.json).

| Field | Meaning |
| --- | --- |
| `schema_version` | Const `rif.runtime.policy/v1` |
| `pack_id` | Stable id for audits (`pack_[a-z0-9_]{3,64}`) |
| `defaults.effect` | `allow` \| `deny` \| `review` when no rule wins |
| `rules[].id` | Unique within pack |
| `rules[].effect` | Decision |
| `rules[].reason_code` | `^[A-Z][A-Z0-9_]{2,63}$` |
| `rules[].priority` | Integer; higher wins among matches (default `0`) |
| `rules[].when` | Boolean expression tree (`all` / `any` / `not` + builtins) |

### 1.3 Built-in predicates (v1 closed set)

| Predicate | Args | True when |
| --- | --- | --- |
| `posture_is` | posture enum | input.posture equals |
| `posture_at_least` | posture enum | input.posture ≥ rung on ladder |
| `mode_in` | string[] | input.mode ∈ list |
| `budget_remaining_gte` | `{requests?, tokens?}` | remaining ≥ each provided field |
| `capability_declared` | `{id}` or `{id, risk_class}` | manifest lists capability (and optional class) |
| `evidence_present` | string[] | every key present in `evidence_availability` |
| `risk_lte` | number 0..1 | `risk_score ≤` arg |
| `host_matches` | pattern[] | host(target) matches exact or `*.suffix` |
| `action_is` | string | action equals |
| `action_prefix` | string | action startswith |
| `intent_hash_eq` | sha256 | intent_hash equals (pin known intents) |

**Forbidden in v1:** arbitrary code, regex unbounded backtracking, remote calls, model prompts, reading process globals, wall-clock comparisons (except frozen `input.as_of` if supplied for tests).

### 1.4 Evaluation input (`PolicyInput`)

```text
PolicyInput:
  mode: str                         # operating mode
  budget: BudgetSnapshot            # requests/tokens/cost remaining
  capability_manifest: ManifestView # declared capabilities + risk_class
  intent: { text?: str, hash: sha256 }
  evidence_availability: map[str, bool] | set[str]
  risk_score: float                 # 0.0 .. 1.0, producer-defined, frozen at eval
  actor: ActorRef
  action: str
  target: str
  environment: str
  posture: Posture                  # frozen at eval start
  environment_snapshot_hash: sha256
  as_of: datetime?                  # optional, for golden tests only
```

All six user-required inputs are first-class. No field is read from ambient agent memory.

---

## 2. Evaluation order

Fixed precedence pipeline (must match explanation `precedence` list):

```text
1. validate_input          → reject malformed input (deny / error)
2. posture_hard_gates      → locked ⇒ deny (short-circuit)
3. compile_match_set       → evaluate `when` for every rule (pure)
4. conflict_resolution     → select winning rule (see §3)
5. effect_emit             → allow | deny | review
6. explain                 → build PolicyExplanation
7. audit_emit              → map to governance.evaluated payload
```

### Pipeline detail

```text
function evaluate(input, pack) -> (Decision, PolicyExplanation):
    assert pack.schema_version == "rif.runtime.policy/v1"
    if input.posture == locked:
        return deny(POSTURE_LOCKED), explain(..., matched="posture.locked", ...)

    matches = []
    for rule in pack.rules:                    # stable pack order for traces
        if eval_when(rule.when, input):
            matches.append(rule)

    winner = resolve(matches, pack.defaults)   # §3
    decision = winner.effect
    return decision, explain(input, pack, matches, winner)
```

**Operational note:** Steps 3–5 must not consult live telemetry windows. Posture is whatever the caller froze into `PolicyInput` (from event log on replay).

---

## 3. Conflict resolution

When multiple rules match:

1. **Highest `priority` wins.**
2. Tie-break by **specificity score** (descending):
   - `+4` if `capability_declared` or concrete `action_is` (not prefix-only)
   - `+2` if `host_matches` present
   - `+2` if `evidence_present` or `risk_lte` present
   - `+1` if `mode_in` or budget predicate present
   - `+0` empty `when.all: []` (catch-all)
3. Remaining ties: **deny beats review beats allow** (fail closed).
4. Still tied: **lexicographically greater `rule.id` wins** (total order, deterministic).
5. If **no** matches: use `pack.defaults.effect` / `defaults.reason_code`.

**Explicit non-algorithm:** “first in file wins” alone is **not** sufficient (today’s exact-match loop + skipped wildcards). Pack order is recorded in explanations for audit, but resolution uses the rules above.

**Conflicts with environment profile:** Environment host allowlists and MCP/package egress flags are compiled into **synthetic rules** at pack load (or injected as a system pack with priority band `1000–1099`) so one resolver applies. They are not a second hidden engine.

Recommended system priority bands:

| Band | Source |
| --- | --- |
| 10_000+ | Hard posture gates (also short-circuit) |
| 1000–1999 | Environment profile / platform constraints |
| 100–999 | Org policy pack |
| 1–99 | App/agent packs |
| 0 | Defaults / catch-all |

---

## 4. Example policies

### 4.1 Allowlisted model HTTP (dev)

```yaml
- id: allow_anthropic
  effect: allow
  reason_code: NETWORK_HOST_ALLOWED
  priority: 100
  when:
    all:
      - { action_is: http.request }
      - { host_matches: ["api.anthropic.com"] }
      - { mode_in: [governed_execute] }
      - { budget_remaining_gte: { requests: 1 } }
      - { risk_lte: 0.5 }
```

### 4.2 Deny when evidence missing

```yaml
- id: deny_without_approval
  effect: deny
  reason_code: EVIDENCE_REQUIRED
  priority: 200
  when:
    all:
      - { action_prefix: "mcp." }
      - { not: { evidence_present: ["capability_token"] } }
```

### 4.3 Elevated posture tightens risk

```yaml
- id: elevated_risk_cap
  effect: deny
  reason_code: RISK_TOO_HIGH_FOR_POSTURE
  priority: 300
  when:
    all:
      - { posture_at_least: elevated }
      - { not: { risk_lte: 0.3 } }
```

### 4.4 Budget exhaustion

```yaml
- id: budget_exhausted
  effect: deny
  reason_code: BUDGET_EXHAUSTED
  priority: 500
  when:
    all:
      - { not: { budget_remaining_gte: { requests: 1 } } }
```

### 4.5 Catch-all deny

```yaml
- id: deny_unknown
  effect: deny
  reason_code: DEFAULT_DENY
  priority: 0
  when: { all: [] }
```

---

## 5. Policy test cases

GaC tests are **data**: input fixture + pack + expected decision/explanation fields. Run in CI with no network.

| Test id | Intent | Expect |
| --- | --- | --- |
| `locked_denies_allowlisted_host` | posture=locked, host=api.anthropic.com | deny `POSTURE_LOCKED` |
| `allow_anthropic_happy` | mode=governed_execute, budget ok, risk 0.2 | allow `NETWORK_HOST_ALLOWED` |
| `deny_blocked_host` | target=blocked.example.com | deny `DEFAULT_DENY` or network synthetic |
| `deny_mcp_without_token` | action=mcp.invoke, evidence lacks token | deny `EVIDENCE_REQUIRED` |
| `deny_budget_zero` | requests_remaining=0 | deny `BUDGET_EXHAUSTED` |
| `elevated_blocks_high_risk` | posture=elevated, risk=0.9 | deny `RISK_TOO_HIGH_FOR_POSTURE` |
| `priority_beats_catch_all` | both allow_anthropic + deny_unknown match | allow (priority 100 > 0) |
| `tie_fail_closed` | two priority=50 rules, allow vs deny | deny |
| `specificity_beats_broad` | broad allow vs specific deny same priority | higher specificity wins |
| `manifest_required` | capability not in manifest | deny (synthetic or rule) |
| `deterministic_repeat` | same input×100 | identical explanation digest |
| `no_hidden_state` | two evals with identical inputs after unrelated live denials | identical result (input posture frozen) |

Fixture layout (implementation slice):

```text
tests/fixtures/policy/
  packs/baseline.v1.yaml
  cases/allow_anthropic_happy.json
  cases/locked_denies_allowlisted_host.json
```

Case file sketch:

```json
{
  "pack": "baseline.v1.yaml",
  "input": { "...": "PolicyInput" },
  "expect": {
    "decision": "allow",
    "reason_code": "NETWORK_HOST_ALLOWED",
    "matched_rule_id": "allow_anthropic",
    "explanation_digest": "optional-sha256"
  }
}
```

---

## 6. Policy explanation format

### 6.1 Object

```text
PolicyExplanation:
  schema_version: rif.runtime.policy-explanation/v1
  explanation_id: ex_ + sha256(canonical(preimage))   # deterministic — no uuid4
  pack_id: str
  pack_hash: sha256                                   # canonical pack bytes
  input_digest: sha256                                # canonical PolicyInput
  decision: allow | deny | review
  reason_code: str
  reason_summary: str
  matched_rule_id: str | null
  matched_rule_priority: int | null
  precedence: [str, ...]                              # pipeline stage names
  candidates:                                         # all matching rules
    - { id, priority, specificity, effect }
  discarded:                                          # non-matching or losers
    - { id, cause: not_matched | lower_priority | tie_fail_closed | ... }
  input_snapshot:
    mode, posture, risk_score, budget, action, target,
    environment, evidence_keys, capability_id?
  posture_before: Posture
  posture_after: Posture                               # usually same at eval; reflexive may update later
  replay_consistent: true                             # must be true for GaC path
```

### 6.2 Mapping to `governance.evaluated`

| Explanation field | Event payload field |
| --- | --- |
| `decision` | `payload.decision` |
| `reason_code` | `payload.reason_code` |
| `reason_summary` | `payload.reason_summary` |
| `matched_rule_id` | `payload.matched_rule` (prefix `policy.`) |
| `precedence` | `payload.precedence` |
| `input_snapshot` / hashes | `environment_snapshot_hash`, `request` |
| `posture_before/after` | same |

### 6.3 Example (abridged)

```json
{
  "schema_version": "rif.runtime.policy-explanation/v1",
  "explanation_id": "ex_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "pack_id": "pack_runtime_default",
  "pack_hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "input_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "decision": "deny",
  "reason_code": "EVIDENCE_REQUIRED",
  "reason_summary": "mcp invoke without capability_token evidence",
  "matched_rule_id": "deny_without_approval",
  "matched_rule_priority": 200,
  "precedence": [
    "validate_input",
    "posture_hard_gates",
    "compile_match_set",
    "conflict_resolution",
    "effect_emit"
  ],
  "candidates": [
    { "id": "deny_without_approval", "priority": 200, "specificity": 6, "effect": "deny" },
    { "id": "deny_unknown", "priority": 0, "specificity": 0, "effect": "deny" }
  ],
  "discarded": [
    { "id": "allow_anthropic", "cause": "not_matched" },
    { "id": "deny_unknown", "cause": "lower_priority" }
  ],
  "input_snapshot": {
    "mode": "governed_execute",
    "posture": "normal",
    "risk_score": 0.4,
    "action": "mcp.invoke",
    "target": "metasploit.local",
    "evidence_keys": [],
    "budget": { "requests_remaining": 10 }
  },
  "posture_before": "normal",
  "posture_after": "normal",
  "replay_consistent": true
}
```

---

## Risks

| Risk | Mitigation |
| --- | --- |
| Dual engines (hardcoded `policy.py` + DSL) drift | Single evaluator; compile env profile into pack; delete parallel paths |
| Priority foot-guns | CI tests for catch-all priority 0; lint rule: deny catch-all required |
| Risk score as opaque vendor metric | Document provenance in input; pin in goldens; never recompute in evaluator |
| YAML ambiguity | Canonicalize to JSON before `pack_hash`; evaluate on canonical form |
| Over-expressive DSL | Keep v1 builtin set closed; no scripts |

---

## Implementation order (DevOps / platform)

### Quick wins

1. Publish this contract + `policy_pack.schema.json` (this slice).
2. Add pack JSON Schema validation in CI.
3. Golden policy case runner (fixtures only; can wrap a pure prototype evaluator).

### Strategic

1. Implement `PolicyEvaluator` conforming to this SPEC; replace `PolicyEngine` path.
2. Compile `environments.yaml` → synthetic system rules.
3. Wire explanations into `governance.evaluated` + replay posture from events.
4. Gate PRs: `policy-test` job must pass on pack changes (governance-as-code).
5. Retire inert `deny_unknown_by_default` skip behavior; express deny-default in DSL.

### Rollback

- Feature flag `RIF_POLICY_ENGINE=legacy|v1`.
- Keep last-known-good `pack_hash` in release metadata; runtime refuses packs that fail schema.

---

## Deferred to v1.1

- Custom predicates / plugins
- Partial wildcards with precedence lattice beyond specificity score
- Interactive `review` workflow / human approval broker
- Multi-pack composition beyond priority bands
- Rego/OPA interop (may compile subset → this DSL later)
