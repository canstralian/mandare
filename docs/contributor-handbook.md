# Contributor Handbook

This handbook is the deeper version of [`CONTRIBUTING.md`](../CONTRIBUTING.md). It focuses on the reasoning expected when changing a governance runtime.

## The contributor loop

```text
question
  -> smallest useful change
  -> executable evidence
  -> review
  -> documentation
  -> merge
```

A good RIF contribution makes the system easier to reason about after the change than before it.

## Change classification

Before coding, classify the change:

| Type | Examples | Required attention |
|---|---|---|
| Documentation | wording, examples, navigation | accuracy and links |
| Behaviour | policy, posture, API, CLI | tests + compatibility |
| Security | auth, secrets, egress, sandbox | threat model + regression test |
| Persistence | record shape, storage, replay | migration/recovery semantics |
| Contract | `spec/` schemas or cross-domain semantics | specification review first |
| Release | packaging, workflow, artifact policy | exact workflow evidence |

## Definition of done

A change is not complete merely because the code runs.

For a behavioural change, the contributor should be able to answer:

- What authority changed?
- What new or changed state can persist?
- Can the result be replayed or inspected?
- What security boundary changed?
- Which tests prove the intended behaviour?
- Which documentation is now canonical?
- What remains deliberately unimplemented?

## Review standard

Reviewers should challenge:

- claims that exceed executable evidence;
- new implicit authority granted to models or integrations;
- duplicated contracts with conflicting precedence;
- persistence changes without recovery tests;
- API examples that are not backed by current routes;
- security language that describes configuration as an achieved outcome;
- performance or availability numbers without a maintained benchmark.

## Documentation discipline

Use explicit status labels where useful:

- **Implemented**
- **Configured**
- **Specification**
- **Planned**
- **Unverified**

Historical release notes should remain historical. Current documentation should not silently rewrite history to make an older release appear to contain newer controls.

## Cross-domain changes

If a change affects identity, capability authority, evidence, replay, provider egress, or another shared contract, consult `spec/README.md` and any open specification review first.

The goal is one authoritative contract rather than two individually reasonable implementations that disagree at the seam.

## Contributor mindset

The most valuable RIF contributions are often not larger features. They are small pieces of engineering that make the governance boundary more explicit:

> **If we cannot point to the code, test, configuration, or recorded run that proves a claim, the claim belongs in the proposal column, not the product column.**
