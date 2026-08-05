# Project Manifest — Dataset Foundry

## What this is

Dataset Foundry is a governed, configuration-driven dataset engineering platform built on RIF Runtime.

It transforms raw source material — Hugging Face datasets, local files, code repositories, agent traces — into reproducible, license-verified, quality-scored training datasets for language model fine-tuning, alignment, and evaluation.

Every stage in the pipeline is policy-evaluated. Every artifact carries lineage. Every build is reproducible.

## Scope

In scope:

- Dataset ingestion from Hugging Face Hub and local filesystems
- License validation and composition policy enforcement
- Schema normalization to canonical DatasetRecord format
- Semantic, AST-based, and conversation-aware chunking
- Quality scoring and filtering
- Manifest generation with full lineage metadata
- Export to JSONL, Parquet, Arrow, and HuggingFace dataset formats
- Profiles for SFT, DPO, RAG, and evaluation datasets
- Plugin system for custom loaders, chunkers, and exporters
- RIF Runtime governance integration for all effectful operations

Out of scope:

- Model training
- Model evaluation beyond dataset quality metrics
- Inference serving
- Autonomous dataset curation without human approval gates
- License interpretation (human legal review required for edge cases)

## Design principles

**Configuration before code.** New datasets, chunkers, export profiles, and quality models are added through configuration. Pipeline logic does not branch on dataset identity.

**Immutable artifacts.** DatasetManifest, DatasetRecord, DatasetChunk, and DatasetLineage are immutable after creation. Mutations produce new versioned artifacts.

**Governed execution.** Every effectful operation (network fetch, file write, HF Hub push) passes through RIF Runtime policy evaluation before execution.

**Explicit lineage.** Every artifact records its source, transformation chain, and the policy decisions that governed its production.

**Reproducibility as a release requirement.** A DatasetBuild is not releasable unless it can be fully reproduced from its manifest and lineage record.

**License-first composition.** No dataset composition proceeds until all source licenses are validated for compatibility with the intended use.

## Core objects

| Object | Role |
| --- | --- |
| DatasetManifest | Root artifact: source registry, build config, lineage summary |
| DatasetRecord | A single normalized data point from a source dataset |
| DatasetChunk | A semantic segment derived from one or more records |
| DatasetAnnotation | Metadata attached to a record or chunk (quality score, labels) |
| DatasetLineage | Provenance chain from source to export artifact |
| DatasetQualityReport | Aggregate quality assessment for a build |
| DatasetExportProfile | Target format, field mapping, and filtering rules |
| DatasetBuild | Versioned, reproducible build artifact |

## Relationship to RIF Runtime

Dataset Foundry uses RIF Runtime as its governance substrate:

- Policy evaluation gates all network, filesystem, and HF Hub operations
- Posture escalation applies when repeated policy denials occur
- Audit trail records every build decision
- Replay engine allows forensic reconstruction of any build

The Dataset Foundry does not modify RIF Runtime's core governance model. It is a consumer, not an extension, of the governance plane.

## Status

| Component | Status |
| --- | --- |
| Specification | In Progress |
| Configuration engine | Planned |
| Dataset registry | Planned |
| HuggingFace loader | Planned |
| License validation | Planned |
| Normalization | Planned |
| Chunking (semantic, AST, conversation) | Planned |
| Quality scoring | Planned |
| Manifest generation | Planned |
| Export profiles (SFT, DPO, RAG, eval) | Planned |
| Plugin API | Planned |
| Benchmarking | Planned |
