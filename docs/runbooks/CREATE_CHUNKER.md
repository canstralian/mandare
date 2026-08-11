# Runbook: Create a Chunker

## When to use this

Use when the built-in chunkers (AST, Markdown, Conversation, Trace, SlidingWindow) do not produce suitable output for a new content type or a new segmentation strategy.

## Prerequisites

- A clear definition of what a "chunk" means for the target content type
- An understanding of the quality and size constraints for the downstream training objective
- A chunker ID (lowercase alphanumeric with hyphens or underscores, ending in `_chunker` — e.g., `sql_chunker`)

## Steps

### 1. Define the chunk boundary

Before writing code, write a plain-language definition:

> A chunk is a single [X] from the source, including [Y] and [Z], but excluding [W].

Example:
> A chunk is a single SQL query block from the source, including the preceding comment if present, but excluding CREATE TABLE statements.

Document this definition in a comment at the top of the implementation file and in `docs/specifications/CHUNKING_SPEC.md`.

### 2. Extend the Chunking Specification

Add a section to `docs/specifications/CHUNKING_SPEC.md` describing:

- The content type this chunker targets
- The chunk boundary definition
- The config fields and their semantics
- The fallback behavior
- Known limitations

Get this reviewed before implementing. The spec is the contract.

### 3. Implement the chunker

Create `src/rif_runtime/dataset/chunkers/<name>.py`:

```python
from rif_runtime.dataset.schemas.dataset import DatasetRecord, DatasetChunk
from rif_runtime.dataset.stages.chunker import ChunkerConfig
from pydantic import BaseModel
import hashlib
from datetime import datetime, timezone


class MySQLChunkerConfig(ChunkerConfig):
    chunker_id: str = "sql_chunker"
    include_preceding_comments: bool = True
    exclude_ddl: bool = True
    max_chunk_tokens: int = 1024
    min_chunk_tokens: int = 32


class SQLChunker:
    chunker_id = "sql_chunker"

    def __init__(self, config: MySQLChunkerConfig) -> None:
        self.config = config

    def chunk(self, record: DatasetRecord) -> list[DatasetChunk]:
        if not record.text:
            return []

        segments = self._segment(record.text)
        chunks = []
        for i, segment in enumerate(segments):
            chunk_id = hashlib.sha256(
                f"{record.id}:{i}".encode()
            ).hexdigest()[:16]
            chunks.append(
                DatasetChunk(
                    id=chunk_id,
                    record_id=record.id,
                    source_id=record.source_id,
                    chunk_index=i,
                    content_type=record.content_type,
                    text=segment,
                    char_count=len(segment),
                    chunker_id=self.chunker_id,
                    created_at=datetime.now(timezone.utc),
                )
            )
        return chunks

    def _segment(self, text: str) -> list[str]:
        # Implementation here
        ...
```

Key requirements:
- Chunk IDs are `sha256(f"{record.id}:{chunk_index}").hexdigest()[:16]` (deterministic).
- `chunker_id` on each chunk matches `self.chunker_id`.
- The chunker is pure: no I/O, no side effects.
- Returns an empty list only if the record has no text.
- Handles edge cases: empty text, single-token text, text longer than `max_chunk_tokens`.

### 4. Register the chunker

```yaml
# configs/chunkers/sql_chunker.yaml
chunker_id: sql_chunker
type: builtin
import_path: rif_runtime.dataset.chunkers.sql.SQLChunker
max_chunk_tokens: 1024
min_chunk_tokens: 32
include_preceding_comments: true
exclude_ddl: true
```

Or for a plugin chunker:

```yaml
chunker_id: sql_chunker
type: plugin
import_path: my_package.chunkers.sql.SQLChunker
plugin_version: "1.0.0"
max_chunk_tokens: 1024
min_chunk_tokens: 32
```

### 5. Map the chunker to a content type

Update the relevant pipeline config to use the new chunker:

```yaml
# configs/pipeline/default.yaml (or a profile-specific config)
chunker_map:
  code: ast_chunker
  conversation: conversation_chunker
  document: markdown_chunker
  trace: trace_chunker
  structured: sql_chunker     # ← map the new chunker
  unknown: sliding_window_chunker
```

Or add a new content type if needed (requires updating the `ContentType` enum and the Classification stage).

### 6. Write tests

Create `tests/dataset/chunkers/test_sql_chunker.py`:

- Test the happy path with representative input
- Test edge cases: empty input, single token, oversized input
- Verify chunk IDs are deterministic (call twice, compare IDs)
- Verify all chunks reference the parent `record_id`
- Verify chunk count is at least 1 for non-empty input
- Verify no chunk's `char_count` mismatches `len(chunk.text)`

### 7. Validate and test

```bash
rif-dataset validate-config
pytest tests/dataset/chunkers/test_sql_chunker.py -v
```

### 8. Document

Update `docs/tools/<name>_chunker.md` with:
- Content type targeted
- Chunk boundary definition
- Config fields
- Failure modes and fallback behavior

### 9. Commit

```bash
git add \
  src/rif_runtime/dataset/chunkers/sql.py \
  configs/chunkers/sql_chunker.yaml \
  tests/dataset/chunkers/test_sql_chunker.py \
  docs/tools/sql_chunker.md \
  docs/specifications/CHUNKING_SPEC.md
git commit -m "feat(chunkers): add SQL chunker for structured content type"
```
