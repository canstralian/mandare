# ADR-0026 — Resource Contracts

## Status

Accepted

## Context

Mandare requires a provider-independent abstraction for addressable
state before implementing repository synchronization, MCP providers,
documentation rendering, or governed knowledge mutation.

## Decision

Introduce the `resources` subsystem.

Core contracts:

- ResourceId
- ResourceReference
- ResourceSnapshot
- ResourceCapabilityDescriptor
- ResourceCapabilityRegistry

The subsystem contains no provider-specific knowledge.

## Consequences

Resources become the stable substrate upon which Providers,
Knowledge, Documentation, Evidence, and Replay are built.

Provider implementations MUST depend on Resources.

Resources MUST NOT depend on Providers.
