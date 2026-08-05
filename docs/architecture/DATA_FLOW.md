# Data Flow

## Record lifecycle

A `DatasetRecord` is created by the Loader and flows through the pipeline, accumulating annotations. It is never mutated in place; each stage returns a new collection.

```
DatasetRecord (raw)
    │
    │ LicenseValidator.validate()
    ▼
DatasetRecord + license_validation annotation
    │
    │ Normalizer.normalize()
    ▼
DatasetRecord (canonical field names, extras preserved)
    │
    │ Classifier.classify()
    ▼
DatasetRecord + content_type annotation
    │
    │ Deduplicator.deduplicate()
    ▼
DatasetRecord (duplicates removed)
    │
    │ Chunker.chunk()
    ▼
DatasetChunk (one or more per record)
    │
    │ Scorer.score()
    ▼
DatasetChunk + quality_score annotation
```

After scoring, chunks below `min_quality_score` or with `license_status=incompatible` are excluded before the Manifest stage.

## Manifest accumulation

The `LineageCollector` accumulates data throughout the run. The `ManifestGenerator` reads from it at the end.

```
LineageCollector:
  - source_lineage: populated by Loader
  - transformation_records: populated by each stage
  - policy_decisions: populated by GovernanceClient
  - stage_reports: populated by each stage
  - exclusion_log: populated by filter steps
```

The `ManifestGenerator` combines all of the above into an immutable `DatasetManifest`.

## Export flow

```
DatasetManifest
    │
    ├── profile = DatasetExportProfile.load(profile_id)
    │
    ├── chunks = filter(manifest.chunks, profile.filters)
    │
    ├── chunks = map(field_mapping, chunks)
    │
    │ Exporter.export(chunks, profile, manifest, context)
    ▼
ExportArtifactRecord
    │
    ├── artifact_path
    ├── artifact_hash (SHA-256)
    ├── record_count
    └── created_at
```

## Governance call flow

```
Pipeline stage needs I/O
    │
    ▼
GovernanceClient.evaluate(
    actor="pipeline.<stage_id>",
    action="READ" | "WRITE" | "PUBLISH",
    target=<resource_ref>,
)
    │
    ▼
PolicyEngine.evaluate(PolicyRequest(...))
    │
    ▼
PolicyDecision(decision="allow" | "deny", reason=..., rule_id=...)
    │
    ├── decision=allow
    │       │
    │       ▼
    │   GovernanceClient logs decision to LineageCollector
    │   Stage proceeds with I/O
    │
    └── decision=deny
            │
            ▼
        GovernanceClient logs decision to LineageCollector
        GovernanceDenied raised
        Pipeline records BuildFailureRecord
        Build halts
```

## Lineage record structure

Each build's complete lineage is recorded in the `DatasetManifest.lineage`:

```
DatasetLineage
  │
  ├── sources[]
  │     └── SourceLineage: registry_entry_id, source_ref, source_version, fetch_timestamp, record_count, hash
  │
  ├── transformations[]
  │     └── TransformationRecord: stage, config_ref, input_count, output_count, excluded_count, exclusion_reasons, timestamp
  │
  ├── policy_decisions[]
  │     └── PolicyDecisionRecord: actor, action, target, decision, reason, rule_id, timestamp
  │
  └── export_artifacts[]
        └── ExportArtifactRecord: profile_id, format, artifact_path, artifact_hash, record_count, created_at
```

## Immutability

All objects in the data flow are immutable Pydantic models. Stages do not mutate inputs; they return new objects.

The only mutable state in the pipeline is the `LineageCollector`, which accumulates records during the run. It is finalized (frozen) when `ManifestGenerator.generate()` is called.

After manifest generation, no further writes to the `LineageCollector` are permitted.

## Streaming vs batch

The pipeline supports streaming mode: `Iterable[DatasetRecord]` means the pipeline can process records one at a time without loading the full dataset into memory.

Stages that require a full pass over the dataset (e.g., exact deduplication with a global hash set) buffer internally. The pipeline does not guarantee streaming semantics for such stages, but it presents a consistent iterable interface at every stage boundary.

The `DatasetManifest` is always generated after all records are processed (non-streaming).
