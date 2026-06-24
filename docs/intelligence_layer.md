# RIF Runtime Intelligence Layer

## Boundary

**RIF decides; intelligence interprets.**

The intelligence layer is optional and is isolated from deterministic enforcement. Policy evaluation, matched rules, posture, confirmation requirements, allowlists, approval gates, audit events, and governance artifacts remain authoritative RIF state.

`POST /v1/intelligence/generate` accepts an immutable deterministic decision snapshot plus explicitly supplied evidence. It returns an explanation or a planning-only security draft. It cannot execute tools, invoke MCP, scan hosts, run commands, approve requests, alter posture, or alter allow/deny decisions.

## Optional OpenAI use

Set `OPENAI_API_KEY` to enable model-assisted interpretation. Input is redacted before leaving the runtime and structured output is validated. Exceptions, malformed output, absent credentials, or timeouts return a deterministic fallback rather than raising or bypassing controls.

Use `RIF_OPENAI_MODEL` to choose the model; the default is `gpt-5-mini`.

## Audit properties

Each response includes:

- the original deterministic decision snapshot unchanged;
- `source` (`llm_assisted` or `deterministic_fallback`);
- `model_used` when available;
- UTC generation timestamp;
- SHA-256 hashes of canonical input and output material;
- warnings for incomplete evidence.

Security-oriented modes generate non-executable drafts only. Any operational action must be compiled into a separate request and pass normal RIF evaluation and approval controls.
