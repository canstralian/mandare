# Tool: conversation_chunker

## Extension point

Chunker

## Content type

`conversation`

## Purpose

Segment multi-turn conversation records into training-ready exchange chunks.

## Input

`DatasetRecord` with `content_type=conversation` and non-empty `messages`.

## Output

`list[DatasetChunk]` — one chunk per conversation exchange.

## Effect

None. Pure computation.

## Config

```yaml
chunker_id: conversation_chunker
type: builtin

# Where to start each chunk
# user_turn: each user message starts a new chunk
# assistant_turn: each assistant message starts a new chunk
exchange_boundary: user_turn

# Maximum number of user+assistant message pairs per chunk
max_turns_per_chunk: 4

# If true, the system message is prepended to every chunk
include_system_prompt: true

# If true, tool call messages are included in chunks
include_tool_calls: true

max_chunk_tokens: 4096
min_chunk_tokens: 32
```

## Chunking strategy

1. Identify the system message (if present) and store it separately.
2. Walk the messages list, identifying exchange boundaries based on `exchange_boundary`.
3. Group messages into exchanges (one user turn + all following assistant turns until the next user turn).
4. Apply `max_turns_per_chunk`: if a chunk would exceed this, force a split before the next user turn.
5. If `include_system_prompt=true`, prepend the system message to each chunk.
6. Serialize each chunk's messages to JSON and store in `DatasetChunk.text`.

## Output format

Each chunk's `text` is a JSON-serialized list of `Message` objects:

```json
[
  {"role": "system", "content": "You are a helpful assistant."},
  {"role": "user", "content": "What is the capital of France?"},
  {"role": "assistant", "content": "Paris."}
]
```

This format is compatible with OpenAI's chat completion format and with the `conversation` field mapping in SFT profiles.

## Chunk metadata

```python
{
    "turn_count": 2,               # number of individual messages in this chunk (excluding system)
    "has_system_prompt": true,
    "message_roles": ["user", "assistant"],
    "chunk_type": "exchange",      # always "exchange" for this chunker
}
```

## Failure modes

| Condition | Behavior |
| --- | --- |
| `messages` is null or empty | Returns empty list |
| Single-turn conversation (one user message, no assistant) | Returns one chunk with the user turn only |
| Very long system prompt | System prompt is truncated to `max_chunk_tokens // 4` tokens before prepending |
| Tool call messages | Included if `include_tool_calls=true`; excluded otherwise |
| Non-alternating role sequence | Messages are processed in order; non-standard sequences produce chunks as-is |

## Known limitations

- Does not split mid-turn. A single message that exceeds `max_chunk_tokens` is included as-is; the chunk will be oversized and may be split by the post-chunking size enforcement.
- System prompt truncation is character-based (a rough token proxy), not token-exact.
- Multi-agent conversations with custom role names (not `system`, `user`, `assistant`, `tool`) are treated as `user` turns for boundary detection purposes.
