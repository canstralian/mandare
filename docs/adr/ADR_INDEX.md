# ADR Index

Architecture Decision Records for RIF Runtime and Dataset Foundry.

## Status legend

| Status | Meaning |
| --- | --- |
| Proposed | Under discussion |
| Accepted | Adopted; governs current implementation |
| Superseded | Replaced by a later ADR |
| Deprecated | No longer relevant |
| Rejected | Considered and declined |

## Records

| ADR | Title | Status | Area |
| --- | --- | --- | --- |
| [ADR-0002](../adr-0002-replayable-governance-memory.md) | Replayable Governance Memory | Accepted | Runtime |
| [ADR-0003](../adr-0003-mcp-security-model.md) | MCP Security Model | Accepted | Security |
| [ADR-0004](../adr-0004-readonly-vs-admin-mcp-workflow.md) | Read-only vs Admin MCP Workflow | Accepted | MCP |
| [ADR-0005](../adr-0005-dev-staging-production-separation.md) | Dev/Staging/Production Separation | Accepted | Environments |
| [ADR-0006](../adr-0006-ai-safety-rationale.md) | AI Safety Rationale | Accepted | Safety |
| [ADR-0007](../adr-0007-database-development-workflow.md) | Database Development Workflow | Accepted | Data |
| [ADR-0008](../adr-0008-agentos-rif-v1-architecture.md) | AgentOS RIF v1 Architecture | Accepted | Runtime |
| [ADR-0026](ADR-0026-resource-contracts.md) | Resource Contracts | Accepted | Architecture |
| [ADR-0027](ADR-0027-cloud-bootstrap-without-ensurepip.md) | Cloud Bootstrap Without ensurepip | Accepted | Infrastructure |
| [ADR-0028](ADR-0028-dataset-foundry-architecture.md) | Dataset Foundry Architecture | Accepted | Dataset Foundry |

## Proposing a new ADR

1. Create `docs/adr/ADR-XXXX-<slug>.md` using the next available number.
2. Set status to `Proposed`.
3. Open a PR with the ADR file only — no implementation.
4. Get review from the relevant agent owner (see `docs/agents/`).
5. Change status to `Accepted` (or `Rejected`) before merging.
6. Update this index.

An ADR must precede any significant architectural change. Implementing first and writing the ADR after is not acceptable.
