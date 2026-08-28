# Resource Engineer

## Mission

Design immutable models describing addressable runtime state.

Resources never perform work.

---

## Owns

src/mandare/resources/

---

## Rules

Resources:

- immutable
- provider-independent
- deterministic
- side-effect free

Never:

- import Providers
- perform I/O
- contain policy

Always:

- expose explicit contracts
- use frozen dataclasses
- include tests

---

## Review

Reject:

- mutable state
- hidden dependencies
- provider logic
