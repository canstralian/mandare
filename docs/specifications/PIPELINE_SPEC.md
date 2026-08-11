# Pipeline Specification

## Purpose

Define the build pipeline: stage ordering, contracts, data flow, and governance integration.

## Pipeline as a directed graph

The build pipeline is a directed acyclic graph (DAG) of stages. Each stage:

- Accepts exactly one input type
- Produces exactly one output type
- Is stateless across records
- Is deterministic given the same configuration
- Does not modify its input

Configuration selects which implementation runs at each stage. The graph topology is fixed. Stage implementations are pluggable.

## Stage graph

```
DatasetRegistryEntry
        │
        ▼
    [Loader]
        │
   Iterable[DatasetRecord] (raw)
        │
        ▼
[License Validation]
        │
   Iterable[DatasetRecord] (annotated)
        │
        ▼
  [Normalization]
        │
   Iterable[DatasetRecord] (canonical)
        │
        ▼
  [Classification]
        │
   Iterable[DatasetRecord] (typed)
        │
        ▼
 [Deduplication]
        │
   Iterable[DatasetRecord] (deduplicated)
        │
        ▼
    [Chunking]
        │
   Iterable[DatasetChunk]
        │
        ▼
[Quality Scoring]
        │
   Iterable[DatasetChunk] (scored)
        │
        ▼
[Manifest Generation]
        │
   DatasetManifest
        │
        ▼
[Export Profile Application]
        │
    DatasetBuild
```

## Stage interface contract

Every stage implements the `PipelineStage` protocol:

```python
class PipelineStage(Protocol[InputT, OutputT]):
    stage_id: str
    config: StageConfig

    def run(self, input: InputT, context: BuildContext) -> tuple[OutputT, StageReport]:
        ...
```

- `run()` must be pure with respect to the pipeline state.
- `run()` must not perform network or filesystem operations without routing through `BuildContext.governance`.
- `run()` must return a `StageReport` even on partial completion.
- Exceptions propagate; the pipeline halts and records a `BuildFailureRecord`.

## BuildContext

Passed to every stage. Provides:

```python
class BuildContext(BaseModel):
    build_id: str
    manifest_id: str
    pipeline_config: PipelineConfig
    governance: GovernanceClient       # wraps PolicyEngine
    lineage: LineageCollector
    logger: BuildLogger
```

Stages call `context.governance.evaluate(request)` before any effectful operation. The call returns a `PolicyDecision`. If `decision == "deny"`, the stage must abort the operation and record the denial in the `StageReport`.

## PipelineConfig

```python
class PipelineConfig(BaseModel):
    loader_id: str
    license_config_id: str
    normalizer_id: str
    classifier_id: str
    deduplicator_id: str
    chunker_map: dict[ContentType, str]   # content_type -> chunker_id
    quality_scorer_id: str
    export_profile_id: str
    fail_on_license_incompatible: bool = True
    fail_on_quality_below: float | None = None
```

## Governance integration

Stages that perform effectful operations declare their effect before execution:

```python
decision = context.governance.evaluate(PolicyRequest(
    actor=f"pipeline.{stage.stage_id}",
    action=effect_type,               # "READ", "WRITE", "PUBLISH"
    target=resource_ref,
))
if decision.decision == "deny":
    raise GovernanceDenied(stage=stage.stage_id, reason=decision.reason)
```

The `GovernanceClient` wraps `RIFRuntime.policy_engine` and records every decision in the audit trail.

Governed stages:

| Stage | Effect | Resource |
| --- | --- | --- |
| Loader | READ | source URL or path |
| Quality Scoring (if plugin) | READ | scoring API endpoint |
| Manifest Generation | WRITE | manifest file path |
| Export Profile Application | WRITE or PUBLISH | artifact path or HF repo |

Non-governed stages (all computation, no I/O):

- License Validation
- Normalization
- Classification
- Deduplication
- Chunking

## Failure semantics

A stage failure:

1. Halts the build immediately.
2. Records a `BuildFailureRecord` with the partial lineage.
3. Does not produce a `DatasetBuild`.
4. Does not delete any already-written artifacts (they become orphaned and are cleaned up by the maintenance job).

Retry is the caller's responsibility. The pipeline itself does not retry.

## Parallelism

The pipeline processes records sequentially within a stage by default.

Parallelism within a stage (e.g., parallel chunk scoring) is an implementation detail of the stage and must not affect the stage's input/output contract or lineage records.

Parallel stage execution (fan-out across multiple datasets) is a pipeline orchestration concern, not a pipeline implementation concern.

## Configuration file layout

```
configs/
  pipeline/
    default.yaml            # default pipeline configuration
    <profile>.yaml          # profile-specific overrides
  datasets/
    <id>.yaml               # DatasetRegistryEntry per dataset
  chunkers/
    <id>.yaml               # chunker configuration
  licenses/
    <id>.yaml               # license definition and compatibility rules
  profiles/
    sft.yaml                # SFT export profile
    dpo.yaml                # DPO export profile
    rag.yaml                # RAG export profile
    evaluation.yaml         # evaluation export profile
  quality/
    <id>.yaml               # quality scorer configuration
```

Pipeline configuration is composable. A profile config may override specific fields of the default pipeline config. Merge is key-level: a scalar or list key in the override replaces the same key in the default entirely. For nested dicts like `chunker_map`, only the specified keys are overridden; unspecified keys inherit from the default. See `docs/specifications/CONFIGURATION_ENGINE.md` for the full merge semantics.
