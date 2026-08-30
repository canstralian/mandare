# Evidence Sufficiency and Change Validation — Pseudocode

**Status:** Draft pseudocode / design input only

**Purpose:** Define a single, evidence-first validation path for proposed code changes before introducing Python implementation. This document is intentionally non-normative until reviewed, tested, and integrated with the runtime contract.

## Design constraints

- Prefer one validation path over parallel validation regimes.
- Keep evidence, inference, assumption, risk, and decision distinct.
- Passing tests is evidence, not proof of semantic safety.
- Unresolved material assumptions must remain visible.
- Do not silently convert unknown information into an assumption.
- A change must not be approved solely because the existing test suite passes.
- Keep the first implementation small and composable.
- Preserve the existing runtime architecture; do not create a competing evidence system.

## Canonical flow

```text
CHANGE REQUEST
    |
    v
COLLECT EVIDENCE
    |
    v
IDENTIFY ASSUMPTIONS
    |
    v
ANALYZE IMPACT
    |
    v
ASSESS RISK
    |
    v
GENERATE COUNTEREXAMPLES
    |
    v
VALIDATE
    |
    v
DECIDE
    |
    +--> APPROVE
    +--> INVESTIGATE
    +--> BLOCK
```

## 1. Evidence

```text
collect_evidence(change):

    evidence = empty collection

    inspect requested behavior
    record directly observed facts

    inspect implementation
    record relevant code facts

    inspect tests
    record what tests actually establish

    inspect documentation and declared contracts
    record relevant contract facts

    inspect call sites and consumers
    record relevant usage facts

    inspect persisted fixtures or examples when applicable
    record compatibility facts

    return evidence
```

### Evidence item

```text
EvidenceItem:
    statement
    source
    status
    relevance
```

Allowed statuses:

```text
OBSERVED
INFERRED
ASSUMED
UNKNOWN
CONTRADICTED
```

Rules:

```text
OBSERVED:
    directly supported by an inspected source

INFERRED:
    derived from observed evidence

ASSUMED:
    temporarily accepted but not established

UNKNOWN:
    relevant information is absent

CONTRADICTED:
    credible evidence conflicts with another claim
```

An `UNKNOWN` must not become `ASSUMED` merely because a decision is inconvenient without the evidence.

## 2. Assumptions

```text
identify_assumptions(change, evidence):

    assumptions = empty collection

    inspect proposed behavior

    for each condition required for the change to be safe:
        if evidence establishes condition:
            record condition as CONFIRMED
        elif evidence contradicts condition:
            record condition as INVALID
        else:
            record condition as UNRESOLVED

    return assumptions
```

Only assumptions that could materially change the safety decision are blocking candidates.

## 3. Impact

```text
analyze_impact(change):

    impact = empty record

    identify modified files
    identify modified symbols
    identify callers and callees
    identify affected input domains
    identify affected output domains
    identify shared mutable structures
    identify declared and observed contracts
    identify persisted-state effects
    identify replay/recovery effects
    identify possible collateral paths

    return impact
```

The system distinguishes **change size** from **change risk**. A small textual change may have a large semantic impact.

## 4. Risk

```text
assess_risk(evidence, assumptions, impact):

    risks = empty collection

    for each impact surface:
        identify failure modes

    for each unresolved material assumption:
        identify the behavior that becomes unsafe if the assumption is false

    for each contradiction:
        identify affected decision

    classify risks as:
        LOW
        MEDIUM
        HIGH
        CRITICAL

    return risks
```

Risk is derived from the consequences of being wrong, not from model confidence alone.

## 5. Counterexamples

```text
generate_counterexamples(change, evidence, assumptions, impact, risks):

    counterexamples = empty collection

    identify the normal successful case

    for each material risk:
        ask:
            "What input, state, caller, or environment would make this change wrong?"

        construct the smallest plausible counterexample

        prioritize cases involving:
            arbitrary user data
            boundary values
            shared structures
            configuration/data collisions
            undocumented consumers
            compatibility behavior
            state transitions
            error paths

        return counterexamples
```

The counterexample stage is adversarial validation, not a second reviewer.

## 6. Validation

```text
validate(change, counterexamples):

    run existing relevant tests

    run targeted regression tests

    run counterexample tests

    validate applicable contracts

    validate persisted/replay behavior when affected

    record every validation result

    return validation_results
```

Validation must distinguish:

```text
PASSED
FAILED
NOT_RUN
NOT_APPLICABLE
```

`NOT_RUN` must never be silently interpreted as `PASSED`.

## 7. Decision

```text
decide(evidence, assumptions, risks, validation_results):

    if any critical contradiction exists:
        return BLOCK

    if any critical validation failure exists:
        return BLOCK

    if any high-risk counterexample fails:
        return BLOCK

    if any unresolved material assumption can change correctness:
        return INVESTIGATE

    if required validation is NOT_RUN:
        return INVESTIGATE

    if required evidence is missing:
        return INVESTIGATE

    return APPROVE
```

The decision must include reasons and supporting evidence references.

## Decision record

```text
Decision:
    outcome
    reasons
    evidence_refs
    assumption_refs
    risk_refs
    validation_refs
```

No decision should require reconstructing its rationale from model conversation history.

## Canonical invariants

1. Passing tests alone cannot produce `APPROVE`.
2. `UNKNOWN` and `ASSUMED` are distinct states.
3. Material unresolved assumptions remain visible to the decision layer.
4. A failed high-risk counterexample prevents approval.
5. `NOT_RUN` validation cannot be treated as success.
6. Observed facts are distinguishable from inferences.
7. Contradictory evidence cannot be silently discarded.
8. The validation path records enough evidence to explain the decision later.
9. The mechanism integrates with the existing evidence architecture rather than introducing a parallel ledger or writer.
10. The implementation should have one obvious orchestration path.

## Canonical adversarial example: configuration/data collision

```text
change:
    normalize a configuration field named "retry"

normal_case:
    configuration.retry is numeric

counterexample:
    user_data = {"retry": "user supplied value"}

required invariant:
    normalization of configuration.retry must not mutate or reinterpret
    unrelated user_data.retry

if the implementation cannot establish this separation:
    evidence = insufficient
    decision = INVESTIGATE or BLOCK
```

## Deliberate non-goals for this iteration

Do not yet define:

- Python classes or concrete module names;
- numerical confidence scoring;
- a second reviewer/validator agent;
- a new persistence backend;
- a new evidence ledger implementation;
- automatic merge authority;
- speculative static-analysis heuristics;
- implementation-specific regular expressions.

Those decisions belong to later iterations after this pseudocode is adversarially reviewed against the existing Mandare contracts.
