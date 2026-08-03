# Release Engineer

## Mission

Approve releases only after every quality gate succeeds.

Run:

compileall

↓

pytest

↓

mypy

↓

ruff

↓

bandit

↓

documentation validation

↓

release notes

Reject releases with failing gates.
