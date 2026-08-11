# System Overview

## Two layers

The Dataset Foundry is built in two layers:

```
┌─────────────────────────────────────────────────┐
│                Dataset Foundry                  │
│                                                 │
│  Registry → Loader → Normalizer → Chunker       │
│      → Quality Scorer → Manifest → Exporter     │
│                                                 │
│  Configuration Engine  │  Plugin Registry       │
└──────────────┬──────────────────────────────────┘
               │ policy evaluation
               ▼
┌─────────────────────────────────────────────────┐
│                RIF Runtime                      │
│                                                 │
│  PolicyEngine  │  GovernanceGraph               │
│  PostureManager │  TelemetryStore               │
│  JsonlStore    │  ReplayEngine                  │
│  Audit API                                      │
└─────────────────────────────────────────────────┘
```

The Dataset Foundry is a consumer of RIF Runtime. It does not extend or modify the governance layer.

## Component map

```
src/rif_runtime/
  dataset/
    registry.py           ConfigurationEngine + DatasetRegistry
    pipeline.py           Pipeline DAG executor
    context.py            BuildContext
    governance.py         GovernanceClient (wraps PolicyEngine)
    lineage.py            LineageCollector
    stages/
      loader.py           Loader stage dispatcher
      license.py          LicenseValidator
      normalizer.py       Normalizer
      classifier.py       Classifier
      deduplicator.py     Deduplicator
      chunker.py          Chunker dispatcher
      scorer.py           Scorer dispatcher
      manifest.py         ManifestGenerator
      exporter.py         Exporter dispatcher
    loaders/
      huggingface.py      HuggingFaceLoader
      local.py            LocalLoader
      url.py              URLLoader
    chunkers/
      ast.py              ASTChunker
      markdown.py         MarkdownChunker
      conversation.py     ConversationChunker
      trace.py            TraceChunker
      sliding_window.py   SlidingWindowChunker
    quality/
      heuristic.py        HeuristicScorer
    exporters/
      jsonl.py            JSONLExporter
      parquet.py          ParquetExporter
      huggingface.py      HuggingFaceExporter
    schemas/
      dataset.py          DatasetRecord, DatasetChunk, DatasetManifest, …
      registry.py         DatasetRegistryEntry, PipelineConfig, …
      profiles.py         DatasetExportProfile, …
```

## Data flow summary

```
configs/datasets/*.yaml
        │
        ▼
DatasetRegistry.lookup(id)
        │
  DatasetRegistryEntry
        │
        ▼
Pipeline.run(entry, profile)
        │
  ┌─────┴──────────────────────────────────────────┐
  │           BuildContext created here             │
  │                                                 │
  │   governance = GovernanceClient(policy_engine)  │
  │   lineage = LineageCollector()                  │
  └──────────────────────────────────────────────┬─┘
                                                 │
  ┌──────────────────────────────────────────────▼─┐
  │   Stage 1: Loader                               │
  │     governance.evaluate("READ", source_ref)     │
  │     → Iterable[DatasetRecord]                   │
  └──────────────────────────────────────────────┬─┘
                                                 │
  [stages 2-7: License, Normalize, Classify,     │
   Deduplicate, Chunk, Score]                    │
                                                 │
  ┌──────────────────────────────────────────────▼─┐
  │   Stage 8: ManifestGenerator                   │
  │     governance.evaluate("WRITE", manifest_path) │
  │     → DatasetManifest                           │
  └──────────────────────────────────────────────┬─┘
                                                 │
  ┌──────────────────────────────────────────────▼─┐
  │   Stage 9: Exporter                             │
  │     governance.evaluate("WRITE"/"PUBLISH", …)   │
  │     → DatasetBuild                              │
  └─────────────────────────────────────────────────┘
```

## Governance integration points

The `GovernanceClient` wraps `RIFRuntime.policy_engine`:

```
GovernanceClient.evaluate(action, target)
    │
    ▼
PolicyEngine.evaluate(PolicyRequest(
    actor="pipeline.<stage_id>",
    action=action,
    target=target,
))
    │
    ▼
PolicyDecision
    │
    ├── decision=allow → operation proceeds
    └── decision=deny → GovernanceDenied raised, build halts
```

Every governance call is recorded in:
- `data/decisions.jsonl` (via JsonlStore)
- The build's `DatasetManifest.policy_decisions`

## Subsystem dependencies

```
dataset.pipeline
    depends on: dataset.context, dataset.stages.*, dataset.schemas.*

dataset.context
    depends on: dataset.governance, dataset.lineage

dataset.governance
    depends on: rif_runtime.policy (PolicyEngine, PolicyRequest)
    does not depend on: any dataset.* module

dataset.stages.*
    depends on: dataset.schemas.*, dataset.loaders.*, dataset.chunkers.*, dataset.quality.*, dataset.exporters.*
    does not depend on: each other (dispatched by pipeline.py)

dataset.schemas.*
    depends on: nothing in rif_runtime or dataset.*
```

No circular imports. Governance is a one-way dependency: dataset → governance → rif_runtime.policy.
