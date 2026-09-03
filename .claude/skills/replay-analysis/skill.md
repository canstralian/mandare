---
name: replay-analysis
description: Validate execution receipts and evidence for deterministic replay and divergence detection.
---

# Replay Analysis

## Mission

Ensure historical executions remain reproducible.

---

## Review

Validate:

- execution receipts
- effect receipts
- evidence bundles
- replay hashes
- divergence

---

## Invariants

Replay:

- never mutates evidence
- never rewrites history
- produces deterministic outcomes

---

## Outputs

- Replay Report
- Divergence Report
- Missing Evidence
- Integrity Assessment

---

## Success Criteria

Replay faithfully reconstructs historical execution without ambiguity.
