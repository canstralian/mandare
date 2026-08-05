# Documentation Index

## Top-level

| Document | Purpose |
| --- | --- |
| [PROJECT_MANIFEST.md](PROJECT_MANIFEST.md) | What the Dataset Foundry is, scope, and goals |
| [ARCHITECTURE.md](ARCHITECTURE.md) | RIF Runtime architecture overview |
| [ROADMAP.md](ROADMAP.md) | Milestones and current status |
| [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) | Contributing and development process |
| [DATA_MODEL.md](DATA_MODEL.md) | Canonical data model reference |
| [API.md](API.md) | API surface reference |

## Specifications

| Document | Purpose |
| --- | --- |
| [specifications/DATASET_FOUNDRY_SPEC.md](specifications/DATASET_FOUNDRY_SPEC.md) | Platform-level specification |
| [specifications/DATASET_SCHEMA.md](specifications/DATASET_SCHEMA.md) | Canonical object model |
| [specifications/PIPELINE_SPEC.md](specifications/PIPELINE_SPEC.md) | Build pipeline specification |
| [specifications/CHUNKING_SPEC.md](specifications/CHUNKING_SPEC.md) | Chunking algorithms and selection |
| [specifications/LICENSE_POLICY.md](specifications/LICENSE_POLICY.md) | License compatibility and enforcement |
| [specifications/QUALITY_MODEL.md](specifications/QUALITY_MODEL.md) | Quality scoring model |
| [specifications/EXPORT_PROFILES.md](specifications/EXPORT_PROFILES.md) | SFT, DPO, RAG, and evaluation export formats |
| [specifications/REGISTRY_SPEC.md](specifications/REGISTRY_SPEC.md) | Dataset registry specification |
| [specifications/PLUGIN_API.md](specifications/PLUGIN_API.md) | Plugin interface contract |
| [specifications/CONFIGURATION_ENGINE.md](specifications/CONFIGURATION_ENGINE.md) | Configuration-driven behavior contract |

## Architecture

| Document | Purpose |
| --- | --- |
| [architecture/SYSTEM_OVERVIEW.md](architecture/SYSTEM_OVERVIEW.md) | High-level system diagram |
| [architecture/DATA_FLOW.md](architecture/DATA_FLOW.md) | Data flow through the pipeline |
| [architecture/PLUGIN_ARCHITECTURE.md](architecture/PLUGIN_ARCHITECTURE.md) | Plugin system design |
| [architecture/MANIFEST_MODEL.md](architecture/MANIFEST_MODEL.md) | Manifest object model |
| [architecture/LINEAGE_MODEL.md](architecture/LINEAGE_MODEL.md) | Lineage tracking model |

## Runbooks

| Document | Purpose |
| --- | --- |
| [runbooks/ADD_DATASET.md](runbooks/ADD_DATASET.md) | Register a new dataset source |
| [runbooks/BUILD_PROFILE.md](runbooks/BUILD_PROFILE.md) | Build an export profile |
| [runbooks/CREATE_CHUNKER.md](runbooks/CREATE_CHUNKER.md) | Implement a new chunking strategy |
| [runbooks/EXPORT_DATASET.md](runbooks/EXPORT_DATASET.md) | Export a processed dataset |
| [runbooks/RELEASE.md](runbooks/RELEASE.md) | Release process |

## Research

| Document | Purpose |
| --- | --- |
| [research/DATASET_SURVEY.md](research/DATASET_SURVEY.md) | Survey of source datasets |
| [research/LICENSE_MATRIX.md](research/LICENSE_MATRIX.md) | License compatibility matrix |
| [research/CHUNKING_RESEARCH.md](research/CHUNKING_RESEARCH.md) | Chunking strategy evaluation |
| [research/QUALITY_BENCHMARKS.md](research/QUALITY_BENCHMARKS.md) | Quality benchmark baselines |

## Architecture Decision Records

| Document | Purpose |
| --- | --- |
| [adr/ADR_INDEX.md](adr/ADR_INDEX.md) | ADR index and status |
| [adr/ADR-0028-dataset-foundry-architecture.md](adr/ADR-0028-dataset-foundry-architecture.md) | Decision: Dataset Foundry as governed platform |

## Agent Definitions

| Document | Owns |
| --- | --- |
| [agents/DATASET_ARCHITECT.md](agents/DATASET_ARCHITECT.md) | Architecture, contracts, manifests |
| [agents/DATASET_ENGINEER.md](agents/DATASET_ENGINEER.md) | Pipeline implementation |
| [agents/LICENSE_GOVERNOR.md](agents/LICENSE_GOVERNOR.md) | License compliance |
| [agents/QUALITY_REVIEWER.md](agents/QUALITY_REVIEWER.md) | Quality metrics and validation |
| [agents/CHUNKING_ENGINEER.md](agents/CHUNKING_ENGINEER.md) | Segmentation algorithms |
| [agents/EXPORT_ENGINEER.md](agents/EXPORT_ENGINEER.md) | Output formats and packaging |
| [agents/BENCHMARK_ENGINEER.md](agents/BENCHMARK_ENGINEER.md) | Dataset evaluation |

## Skills

| Document | Workflow |
| --- | --- |
| [skills/ingest_dataset.md](skills/ingest_dataset.md) | Load a dataset from source |
| [skills/normalize_dataset.md](skills/normalize_dataset.md) | Normalize to canonical schema |
| [skills/validate_license.md](skills/validate_license.md) | Validate license compatibility |
| [skills/semantic_chunking.md](skills/semantic_chunking.md) | Segment records semantically |
| [skills/score_quality.md](skills/score_quality.md) | Apply quality scoring model |
| [skills/generate_manifest.md](skills/generate_manifest.md) | Produce a DatasetManifest |
| [skills/export_profile.md](skills/export_profile.md) | Emit a target export format |
| [skills/benchmark_dataset.md](skills/benchmark_dataset.md) | Evaluate dataset quality |

## Tools

| Document | Component |
| --- | --- |
| [tools/huggingface_loader.md](tools/huggingface_loader.md) | HuggingFace Hub loader |
| [tools/local_loader.md](tools/local_loader.md) | Local filesystem loader |
| [tools/ast_chunker.md](tools/ast_chunker.md) | AST-based code chunker |
| [tools/markdown_chunker.md](tools/markdown_chunker.md) | Markdown document chunker |
| [tools/conversation_chunker.md](tools/conversation_chunker.md) | Conversation turn chunker |
| [tools/trace_chunker.md](tools/trace_chunker.md) | Agent trace chunker |
| [tools/jsonl_exporter.md](tools/jsonl_exporter.md) | JSONL exporter |
| [tools/parquet_exporter.md](tools/parquet_exporter.md) | Parquet exporter |
| [tools/hf_exporter.md](tools/hf_exporter.md) | HuggingFace Hub exporter |
