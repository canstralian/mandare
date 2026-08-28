# ADR-0005: Dev / Staging / Production Project Separation

## Status
Proposed (captured 2026-07-09)

## Context
Environment-scoped allowed hosts already exist in the runtime's trust model
(`config/environments.yaml`). External state (e.g. Supabase projects) needs
the same scoping so a mistake or compromised agent in dev cannot touch
production data.

## Decision
Split external provider state into three isolated projects — dev, staging,
production — mirroring the runtime's environment profiles (`Mandare`,
`RIF_Research`, `RIF_CI`):

- **Dev** — agents read and write freely; schema is disposable; migrations
  are authored and first applied here
- **Staging** — receives migrations only through CI; used for integration
  verification against production-shaped data
- **Production** — agents get read-only access at most; schema changes arrive
  exclusively as reviewed SQL migrations promoted through CI; no MCP admin
  connection targets production

## Consequences
- Blast radius of any agent action is bounded to its environment
- Promotion between environments is a pipeline event, never an interactive
  session
