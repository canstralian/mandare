---
name: provider-review
description: Validate provider implementations against runtime contracts and governance requirements.
---

# Provider Review

## Mission

Providers execute interactions.

Providers never own policy.

---

## Validate

- stable interfaces
- explicit capabilities
- effect classification
- error mapping
- receipt generation
- replay support

---

## Reject

- provider-specific business logic
- hidden authentication
- policy enforcement inside providers
- mutable global state

---

## Success Criteria

Providers remain interchangeable behind stable contracts.
