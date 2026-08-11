# Contributor Handbook

## Purpose

This handbook defines how to contribute safely and consistently to RIF Runtime.

## Workflow

1. Create a branch
2. Make focused changes
3. Add or update tests
4. Run validation
5. Submit PR
6. Address review feedback

## Branch Naming

- feat/*
- fix/*
- docs/*
- refactor/*
- chore/*

## Commit Format

```text
type(scope): summary
```

Examples:

- feat(governance): add constrained approval
- fix(replay): preserve action ordering

## Documentation Requirements

Every behavioral change must include:

- motivation
- design impact
- governance impact
- replay impact
- migration notes

## Review Expectations

- correctness
- policy compliance
- replayability
- security
- observability
- documentation

## Definition of Done

- tests pass
- docs updated
- telemetry considered
- security reviewed
- replay impact assessed
