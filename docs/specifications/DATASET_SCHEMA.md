# Dataset Schema Specification

## Overview

All data in the Dataset Foundry pipeline flows through a fixed set of canonical objects. These objects are Pydantic v2 models, immutable after construction, and serializable to JSON without loss.

## DatasetRegistryEntry

The declarative definition of a dataset source.

```python
class DatasetRegistryEntry(BaseModel):
    id: str                          # unique identifier, slug format
    name: str                        # human-readable name
    source_type: SourceType          # huggingface | local | url
    source_ref: str                  # HF dataset id, path, or URL
    source_version: str | None       # HF revision, git sha, or None
    license_id: str                  # references configs/licenses/<id>.yaml
    content_types: list[ContentType] # expected content types
    config: dict[str, Any]           # source-specific loader configuration
    enabled: bool = True
    tags: list[str] = []
```

## DatasetRecord

A single normalized data point. Immutable after creation.

```python
class DatasetRecord(BaseModel):
    id: str                          # deterministic hash of source + index
    source_id: str                   # references DatasetRegistryEntry.id
    source_index: int                # original position in source dataset
    content_type: ContentType        # code | conversation | document | trace | structured | unknown
    text: str | None                 # primary text content
    messages: list[Message] | None   # for conversation records
    metadata: dict[str, Any]         # source metadata preserved verbatim
    extra: dict[str, Any]            # fields not mappable to canonical schema
    license_status: LicenseStatus    # compatible | incompatible | review_required | unknown
    annotations: list[Annotation] = []
    created_at: datetime
```

## DatasetChunk

A semantic segment derived from one DatasetRecord.

```python
class DatasetChunk(BaseModel):
    id: str                          # deterministic hash of record id + chunk index
    record_id: str                   # parent DatasetRecord.id
    source_id: str                   # inherited from parent record
    chunk_index: int                 # position within parent record
    content_type: ContentType        # may differ from parent if reclassified
    text: str
    token_count: int | None          # populated by quality scoring stage
    char_count: int
    chunker_id: str                  # references configs/chunkers/<id>.yaml
    quality_score: float | None      # populated by quality scoring stage
    annotations: list[Annotation] = []
    metadata: dict[str, Any] = {}
    created_at: datetime
```

## Message

A single turn in a conversation record.

```python
class Message(BaseModel):
    role: Role                       # system | user | assistant | tool
    content: str
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None
```

## Annotation

Metadata attached to a record or chunk.

```python
class Annotation(BaseModel):
    key: str
    value: Any
    source: str                      # which stage or tool produced this annotation
    created_at: datetime
```

## DatasetManifest

Root artifact for a dataset build. Immutable.

```python
class DatasetManifest(BaseModel):
    id: str                          # unique build identifier
    version: str                     # semver
    created_at: datetime
    sources: list[DatasetRegistryEntry]
    pipeline_config: PipelineConfig
    stage_reports: dict[str, StageReport]
    policy_decisions: list[PolicyDecisionRecord]
    record_count: int
    chunk_count: int
    license_summary: LicenseSummary
    quality_summary: QualitySummary
    lineage: DatasetLineage
    reproducible: bool               # True if all sources are pinned
```

## DatasetLineage

Provenance chain from sources to export artifact.

```python
class DatasetLineage(BaseModel):
    manifest_id: str
    sources: list[SourceLineage]
    transformations: list[TransformationRecord]
    policy_decisions: list[PolicyDecisionRecord]
    export_artifacts: list[ExportArtifactRecord]
```

## SourceLineage

```python
class SourceLineage(BaseModel):
    registry_entry_id: str
    source_ref: str
    source_version: str | None
    fetch_timestamp: datetime
    record_count: int
    hash: str                        # SHA-256 of fetched content
```

## TransformationRecord

```python
class TransformationRecord(BaseModel):
    stage: str                       # normalization | chunking | quality_scoring | etc.
    config_ref: str                  # path to config file used
    input_count: int
    output_count: int
    excluded_count: int
    exclusion_reasons: dict[str, int]
    timestamp: datetime
```

## DatasetExportProfile

Defines the output format, field mapping, and filtering rules for a build target.

```python
class DatasetExportProfile(BaseModel):
    id: str
    name: str
    format: ExportFormat             # jsonl | parquet | arrow | huggingface
    profile_type: ProfileType        # sft | dpo | rag | evaluation | custom
    field_mapping: dict[str, str]    # canonical field -> output field name
    filters: list[FilterRule]
    min_quality_score: float = 0.5
    max_token_count: int | None = None
    min_token_count: int | None = None
    permit_review_required: bool = False
    hf_repo_id: str | None = None    # for huggingface format
    compression: str | None = None
```

## DatasetBuild

The versioned, releasable output of a complete pipeline run.

```python
class DatasetBuild(BaseModel):
    id: str
    manifest_id: str
    version: str
    profile_id: str
    artifact_path: str
    artifact_hash: str               # SHA-256 of the export artifact
    record_count: int
    created_at: datetime
    reproducible: bool
    governance_summary: GovernanceSummary
```

## DatasetQualityReport

Aggregate quality assessment for a build.

```python
class DatasetQualityReport(BaseModel):
    manifest_id: str
    total_chunks: int
    scored_chunks: int
    excluded_chunks: int
    score_distribution: dict[str, float]  # percentile -> score
    mean_score: float
    median_score: float
    threshold_used: float
    scorer_id: str
    created_at: datetime
```

## Enumerations

```python
class SourceType(StrEnum):
    huggingface = "huggingface"
    local = "local"
    url = "url"

class ContentType(StrEnum):
    code = "code"
    conversation = "conversation"
    document = "document"
    trace = "trace"
    structured = "structured"
    unknown = "unknown"

class LicenseStatus(StrEnum):
    compatible = "compatible"
    incompatible = "incompatible"
    review_required = "review_required"
    unknown = "unknown"

class ExportFormat(StrEnum):
    jsonl = "jsonl"
    parquet = "parquet"
    arrow = "arrow"
    huggingface = "huggingface"

class ProfileType(StrEnum):
    sft = "sft"
    dpo = "dpo"
    rag = "rag"
    evaluation = "evaluation"
    custom = "custom"

class Role(StrEnum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"
```

## Serialization rules

- All datetimes are UTC ISO 8601 strings.
- All IDs are lowercase alphanumeric with hyphens.
- `extra` fields round-trip through JSON without loss.
- `None` fields are omitted from JSON serialization (`model_dump(exclude_none=True)`).
- Enums serialize as bare string values (StrEnum).
