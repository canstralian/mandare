# Tool: trace_chunker

## Extension point

Chunker

## Content type

`trace`

## Purpose

Segment agent execution traces into tool-call-centric chunks, each containing one tool invocation and its surrounding context.

## Input

`DatasetRecord` with `content_type=trace` and non-empty `messages`.

## Output

`list[DatasetChunk]` — one chunk per tool call in the trace.

## Effect

None. Pure computation.

## Config

```yaml
chunker_id: trace_chunker
type: builtin

# Number of preceding assistant turns to include before the tool call
include_preceding_turns: 1

# Number of turns after the tool result to include
include_following_turns: 0

# If true, include the tool result message in the chunk
include_tool_result: true

# If true, include the system message at the start of each chunk
include_system_prompt: false

max_chunk_tokens: 2048
min_chunk_tokens: 32
```

## Chunking strategy

A trace record is a sequence of messages that includes at least one tool call:

```
system → user → assistant (with tool_calls) → tool (result) → assistant → ...
```

The trace chunker identifies each `assistant` message containing `tool_calls` and builds a chunk around it:

1. Collect up to `include_preceding_turns` assistant/user turns before the tool call.
2. Include the assistant message with `tool_calls`.
3. If `include_tool_result=true`, include the following `tool` role message(s).
4. If `include_following_turns > 0`, include that many subsequent turns after the tool result.
5. If `include_system_prompt=true`, prepend the system message.
6. Serialize to JSON and store in `DatasetChunk.text`.

## Chunk metadata

```python
{
    "tool_name": "get_file_contents",
    "tool_call_id": "call_abc123",
    "tool_call_index": 2,          # position in the trace
    "total_tool_calls": 7,         # total tool calls in the parent trace
    "has_tool_result": true,
}
```

## Records without tool calls

If a trace record has no messages with `tool_calls`, the trace chunker falls back to `ConversationChunker`. The fallback is recorded in `StageReport.exclusion_reasons["chunker_fallback"]`.

## Output format

Same as `conversation_chunker`: JSON-serialized list of `Message` objects in `DatasetChunk.text`.

## Use cases

Trace chunks are suitable for:

- **Tool-use SFT**: training a model to invoke tools correctly given a task
- **Tool selection DPO**: pairing correct and incorrect tool invocations as chosen/rejected
- **Agentic evaluation**: benchmarking tool selection and parameter accuracy

## Failure modes

| Condition | Behavior |
| --- | --- |
| No tool calls in trace | Falls back to `ConversationChunker` |
| Tool call without result | Chunk includes tool call but omits result message |
| Multiple tool calls in one assistant turn | Each tool call produces a separate chunk sharing the same preceding context |
| Very long tool result | Tool result is included as-is; may cause chunk to exceed `max_chunk_tokens` |
