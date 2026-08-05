# Tool: ast_chunker

## Extension point

Chunker

## Content type

`code`

## Purpose

Segment Python source code into semantically meaningful chunks at AST node boundaries (functions, classes, module-level constants).

## Input

`DatasetRecord` with `content_type=code` and non-empty `text`.

## Output

`list[DatasetChunk]` — one chunk per top-level AST definition.

## Effect

None. Pure computation.

## Config

```yaml
chunker_id: ast_chunker
type: builtin

# Language (only python supported)
language: python

# If true, each method within a class is extracted as a separate chunk
# in addition to the full class chunk
extract_methods: false

# If true, the module's import block is prepended to each chunk
include_imports: true

# Max tokens per chunk (enforced after extraction)
max_chunk_tokens: 1024

# Min tokens per chunk (undersized chunks are merged with the preceding chunk)
min_chunk_tokens: 32
```

## Chunking strategy

The AST chunker parses the input with Python's `ast` module. It identifies top-level definitions:

1. **Import block**: all leading `import` and `from ... import` statements are collected into a single block (not emitted as a standalone chunk unless `include_imports=false`).

2. **Module-level assignments and constants**: `NAME = ...` at module level, not inside a class or function. Each assignment is its own chunk (or merged with adjacent assignments if small).

3. **Functions**: `def` statements at module level. One chunk per function, including its docstring. If `include_imports=true`, the import block is prepended.

4. **Classes**: `class` statements at module level. One chunk per class, including all methods. If `extract_methods=true`, each method is also extracted as a separate chunk.

5. **Type aliases and dataclasses**: treated as constants/assignments.

## Chunk IDs

```python
chunk_id = sha256(f"{record.id}:{chunk_index}").hexdigest()[:16]
```

`chunk_index` is the zero-based position of the chunk within the record's output list.

## Fallback

If `ast.parse()` raises a `SyntaxError`, the chunker raises `ChunkerParseError`. The pipeline falls back to `SlidingWindowChunker`.

## Failure modes

| Condition | Behavior |
| --- | --- |
| `SyntaxError` from `ast.parse` | Raises `ChunkerParseError`; pipeline falls back |
| Empty file (no definitions) | Returns a single chunk containing the full file content |
| All definitions exceed `max_chunk_tokens` | Each definition is split with `SlidingWindowChunker` |
| File is only imports (no definitions) | Returns a single chunk of the import block |

## Known limitations

- Python only (current implementation).
- Does not handle multi-file modules or `__init__.py` re-exports.
- Class methods are not disambiguated from standalone functions when `extract_methods=true` (they share the same chunk structure).
- Async functions and generators are treated identically to regular functions.
- Decorator resolution is not performed; decorators are included in the chunk but not interpreted.
