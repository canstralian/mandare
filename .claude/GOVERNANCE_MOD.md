# Claude Code governance mod

Status: **v0.1 host-enforcement adapter**.

This mod places a deterministic guard around Claude Code `tool.call` events. It is intentionally not a second Mandare policy engine. Mandare's runtime remains the authority for governed capabilities; this adapter narrows Claude Code's host behavior until the runtime authority primitive is integrated in a later slice.

## Invariants

- Model intent is not authority.
- Recognized external writes and destructive actions require a live, one-shot human approval.
- Unknown tools and unknown MCP operations fail closed.
- Dismissed or non-interactive approval prompts are refusals.
- A guard exception or timeout fails closed through the hook registration's `.catch(...)` handler.
- Approval is bound to a SHA-256 fingerprint of the tool name, tool-use identifier when present, and canonicalized arguments. No reusable approval token is exposed to the model.
- Guard evidence stores hashes and decision metadata, not raw tool arguments or outputs.

## Effect classes

| Effect | v0.1 behavior |
| --- | --- |
| `READ` | pass through |
| `LOCAL_WRITE` | defer to normal Claude Code permissions |
| `LOCAL_EXECUTION` | defer to normal Claude Code permissions |
| `NETWORK_READ` | defer to normal Claude Code permissions |
| `EXTERNAL_WRITE` | require `Approve once` |
| `DESTRUCTIVE` | require `Approve once` |
| `UNKNOWN` | deny |

MCP classification is verb-based and deny-by-default. Add a reviewed classification before relying on a newly introduced MCP operation.

Bash classification is deliberately conservative but is **not** a shell parser or sandbox. Indirection, aliases, generated scripts, or an unrecognized spelling can evade text classification. Remote API permissions, branch protection, credential scope, OS/container isolation, and managed Claude policy remain stronger enforcement boundaries.

## Evidence

Guarded calls append a bounded hash-linked suffix to the plugin store under `mandare.governance.evidence.v1`. Records contain the effect, tool name, canonical input hash, decision, timestamp, and previous-record hash. This is useful for local reconstruction and alteration detection within the retained suffix; it is not an immutable or complete audit log. A process with the user's permissions can replace or truncate the plugin store.

## Mod-chain limitation

A user-installed mod is not an unbypassable root of trust. Other mods can run before or after it. This v0.1 approval binds the event as Mandare sees it at its `tool.call` boundary; a later mod could rewrite an event after approval. High-assurance deployments should place governance in managed/prepend policy and enforce the same authority at the remote capability boundary. A later Mandare slice will move exact single-use authority into the runtime rather than treating the host prompt as the final trust boundary.

## Validate

Requires Claude Code 2.1.287 or later for mods.

From `.claude/`:

```bash
claude plugin validate .
claude plugin test
claude plugin eval . --case external-write-requires-approval --runs 1 --ablation none --no-publish --allow-tools 'Bash(git push *)'
```

The eval is intentionally non-interactive: `$.ui.ask` has nobody to answer, so the guarded push must be denied. Run evals only in an isolated disposable workspace even though this case is expected to block the command.
