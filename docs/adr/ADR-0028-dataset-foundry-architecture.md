# ADR-0028 — Dataset Foundry Architecture

## Status

Accepted

## Context

RIF Runtime is a governed agent runtime with a policy engine, governance graph, posture management, and an audit trail. These primitives — policy evaluation, deny-by-default trust model, replayable audit log — are directly applicable to dataset engineering workflows where:

- Dataset fetches from external sources are effectful and should be governed
- License decisions must be recorded and auditable
- Dataset builds should be reproducible and their lineage inspectable
- Publication to HuggingFace Hub is a high-stakes operation requiring explicit policy approval

The need exists for a principled platform that:
1. Manages a registry of approved source datasets
2. Runs a configurable pipeline (ingest → validate → normalize → chunk → score → export)
3. Produces governed, auditable, reproducible dataset builds
4. Integrates with the existing RIF Runtime governance layer rather than duplicating it

## Decision

Introduce the **Dataset Foundry** as a governed dataset engineering platform built on RIF Runtime.

Key decisions:

### 1. Consumer, not extension

The Dataset Foundry is a consumer of RIF Runtime, not an extension of it. It calls `PolicyEngine.evaluate()` for effectful operations; it does not modify the governance layer.

### 2. Configuration over code

Pipeline behavior is defined in YAML configuration files. The pipeline executor reads configuration and dispatches to registered components. No pipeline code branches on dataset identity or content.

### 3. Configuration directory under `configs/`

```text
configs/
  pipeline/   datasets/   chunkers/   licenses/
  profiles/   quality/    exporters/  plugins/
```

All configurations are checked into git. Changes to configuration files are code changes with the same review requirements as Python changes.

### 4. Canonical schema in `src/rif_runtime/dataset/schemas/`

A fixed set of Pydantic v2 models: `DatasetRecord`, `DatasetChunk`, `DatasetManifest`, `DatasetBuild`, etc. All stages consume and produce these types. No stage invents its own intermediate format.

### 5. Plugin API for extensibility

Custom loaders, chunkers, scorers, and exporters are plugins implementing typed protocols. Plugins are registered in configuration and loaded at startup. They run in-process.

### 6. Immutable artifacts

All artifacts (records, chunks, manifests, builds) are immutable after creation. Mutations produce new versioned artifacts. The pipeline never modifies its inputs.

### 7. Full lineage in the manifest

The `DatasetManifest` records every source, configuration, stage output, and policy decision in a single artifact. Lineage is not a separate system; it is part of the manifest model.

### 8. Module layout

```text
src/rif_runtime/
  dataset/
    registry.py     pipeline.py     context.py     governance.py     lineage.py
    stages/         loaders/        chunkers/       quality/          exporters/
    schemas/
```

The `dataset/` subpackage depends on `rif_runtime.policy` (one-way). It does not depend on `api.py`, `cli.py`, or `runtime.py` directly.

### 9. CLI extension

A `rif-dataset` CLI (separate Typer app or subcommand) exposes:

```text
rif-dataset build
rif-dataset validate-config
rif-dataset validate-registry
rif-dataset validate-manifest
rif-dataset verify-build
rif-dataset verify-lineage
rif-dataset publish
rif-dataset license-report
rif-dataset ingest (for testing)
```

## Consequences

### Positive

- Policy evaluation for all dataset I/O is inherited from the existing RIF Runtime governance layer.
- The audit trail (`/v1/audit`, `decisions.jsonl`) captures all dataset pipeline decisions without additional instrumentation.
- The existing replay engine can reconstruct governance decisions made during dataset builds.
- Dataset builds are reproducible: the manifest fully describes the inputs and transformations.
- New datasets, chunkers, and profiles can be added without modifying pipeline code.

### Negative

- Adds a new subpackage (`dataset/`) and a new config directory tree to the repository.
- The `configs/` directory will grow as more datasets and profiles are added; requires discipline to keep organized.
- Plugin governance (ensuring plugins call governance before I/O) is enforced by convention, not by the runtime.

### Neutral

- The Dataset Foundry does not change the RIF Runtime API surface, governance model, or posture management.
- The `rif-dataset` CLI is additive; it does not change `rif serve`, `rif check`, or `rif replay`.

## Alternatives considered

### A — Standalone repository

A separate repository for the Dataset Foundry that calls RIF Runtime over HTTP.

Rejected: HTTP coupling introduces latency for governance calls, requires network availability, and complicates testing. The governance layer is better consumed as a library.

### B — No governance integration

A standalone dataset pipeline without RIF Runtime integration.

Rejected: Loses the primary value proposition — governed, auditable dataset builds. License and publication decisions must be explicitly recorded.

### C — Database-backed registry

Replace YAML configs with a database.

Rejected: YAML files are versionable, diffable, and reviewable via git. A database adds operational complexity without improving the governance model.
