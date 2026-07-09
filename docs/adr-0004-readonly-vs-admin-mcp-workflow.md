# ADR-0004: Read-only vs Admin MCP Workflow

## Status
Proposed (captured 2026-07-09)

## Context
Least privilege must be enforced by credentials, not by prompt instructions.
An agent holding only a read-only token cannot be prompt-injected into
destructive writes.

## Decision
Maintain two distinct MCP connection tiers per external service:

1. **Read-only tier (default)** — day-to-day agent work: queries, fetches,
   schema listing. Credentials are scoped read-only at the provider level.
2. **Admin tier (deliberate use only)** — schema changes, migrations,
   deletions, permission changes. Human-supervised sessions only; never
   granted to autonomous or scheduled agents; every use logged as a governed
   decision.

## Consequences
- Two connector entries per service; the admin connector stays disabled or
  disconnected between uses
- Escalation from read-only to admin is an explicit, logged event (maps to
  the planned challenge/escalation decision model)
