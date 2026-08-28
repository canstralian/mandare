# ADR-0007: Recommended Database Development Workflow

## Status
Proposed (captured 2026-07-09)

## Context
The data model is being prepared for migration into Supabase. Designing the
database ad hoc — or letting docs lag the code, a known failure mode of this
project — must be avoided.

## Decision
Database and schema work follows this pipeline:

1. **Specify** — the canonical schema lives as documentation first:
   `docs/DATA_MODEL.md` (mirrored to the Mandare Notion hub). Data-model
   changes start as edits to the spec.
2. **Author migrations** — each accepted spec change becomes a SQL migration
   file (e.g. `supabase/migrations/`), reviewed like any other code.
3. **Apply to dev** — migrations are applied to the dev project (Supabase
   MCP `apply_migration` or CLI) and verified with tests and smoke checks.
4. **Promote via CI** — staging and production only ever receive migrations
   through the CI pipeline.
5. **Document** — the spec and docs are updated in the same change set; docs
   lagging code is treated as a defect.

## Consequences
- The schema spec is version-controlled and reviewable before any SQL exists
- Production schema changes are always reviewed, pipelined, and reversible
- Agent sessions use the read-only MCP tier (ADR-0004) unless a human
  explicitly escalates
