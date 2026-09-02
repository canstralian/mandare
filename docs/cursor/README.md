# Cursor CLI hardening for RIF Runtime

This directory documents the **RIF-optimized local Cursor Agent CLI** baseline.
Project-scoped files live under `.cursor/`; the global template is copied to the
operator's machine.

## Design goals

| Choice | Benefit | Cost |
| --- | --- | --- |
| Sandbox `workspace_readwrite` | Safer writes; cleaner evidence/replay | Occasional permission prompts |
| Restricted `WebFetch` domains | Limits accidental exfiltration | Add domains when a new host is needed |
| No open web search in allowlist | More deterministic agent context | Less autonomous research |
| Shell kept for build/test | Full `ruff` / `mypy` / `pytest` / `rif` workflow | Highest-risk capability |
| Allowlist approval mode | Deterministic trusted actions | Prompts for anything off-list |

## Files

| Path | Scope | Role |
| --- | --- | --- |
| [`.cursor/cli.json`](../../.cursor/cli.json) | Project | Permissions only (Cursor project override) |
| [`.cursor/sandbox.json`](../../.cursor/sandbox.json) | Project | Workspace-write sandbox + deny-by-default network |
| [`.cursor/mcp.json`](../../.cursor/mcp.json) | Project | Cursor MCP connector declarations (not RIF policy) |
| [`.cursor/rules/rif-evidence-first.mdc`](../../.cursor/rules/rif-evidence-first.mdc) | Project | Always-on evidence-first guardrail |
| [`cli-config.json.example`](./cli-config.json.example) | Global template | Full `~/.cursor/cli-config.json` for local CLI |

## Apply on your machine

1. Copy the global template (once per machine):

```bash
cp docs/cursor/cli-config.json.example ~/.cursor/cli-config.json
```

2. Keep the repo files checked out (already committed):

- `.cursor/cli.json`
- `.cursor/sandbox.json`
- `.cursor/mcp.json`
- `.cursor/rules/rif-evidence-first.mdc`

3. Restart the Cursor Agent CLI (or run `/sandbox` and confirm sandbox is
   enabled with network limited to config + defaults).

4. Default CLI mode is Agent (`defaultBehavior: agent` is implicit). Prefer
   Plan/Ask when exploring; keep Max Mode off for routine RIF work.

## Schema mapping notes

Cursor's published CLI schema differs slightly from informal tool-name lists:

- Domain allowlisting is expressed as `WebFetch(host)` entries in
  `permissions.allow`, not a separate `webFetchDomainAllowlist` field.
- Project `.cursor/cli.json` may configure **permissions only**; sandbox mode,
  approval mode, display, and attribution belong in `~/.cursor/cli-config.json`.
- Filesystem sandbox policy for terminal commands is `.cursor/sandbox.json`
  (`type: workspace_readwrite`, `networkPolicy.default: deny`).
- Built-in agent tools such as Glob/Grep/Edit are not separate CLI permission
  tokens; Read/Write/Shell/WebFetch/Mcp cover the documented surface.
- `WebSearch` and `GenerateImage` are intentionally omitted from the allowlist
  (unrelated / non-deterministic for runtime engineering).

## Allowed WebFetch / sandbox domains

- `github.com`, `*.github.com`
- `raw.githubusercontent.com`, `*.githubusercontent.com`
- `huggingface.co`, `*.huggingface.co`
- `api.openai.com`
- `developers.cloudflare.com`
- `docs.anthropic.com`
- `modelcontextprotocol.io`, `*.modelcontextprotocol.io`
- `airtable.com`, `*.airtable.com`
- `mcp.supabase.com`, `supabase.com`, `*.supabase.com`

Sandbox also allows PyPI hosts so `pip install` works under
`user_config_with_defaults` without opening the wider web.

## MCP allowlist

These MCP servers are permitted when configured in `.cursor/mcp.json` (or a
local `mcp.json`):

- `filesystem`
- `github`
- `rif-evidence`
- `rif-replay`
- `rif-policy`
- `airtable`
- `supabase`

The committed `supabase` entry is a Cursor IDE connector for project
`xbpujhxecuebpdizhnqp`. It is configuration, not a RIF authorization
decision: it does not grant the runtime policy authority, does not replace
`SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_ANON_KEY`, and does
not make model output authoritative. Authentication still happens in Cursor
when the operator connects the server. The declared feature set
(`docs`, `account`, `database`, `debugging`, `development`, `functions`,
`branching`) is operator-supplied; treat write-capable features as
human-supervised, consistent with ADR-0004's proposed read-only vs admin
split.

## Evidence-first rule

> Never use network access to obtain implementation details when the repository
> already contains the relevant source, tests, schemas, or documentation.
> Prefer repository evidence over external evidence.

Encoded in `.cursor/rules/rif-evidence-first.mdc` with `alwaysApply: true`.

## Trade-offs accepted

- Shell remains allowed for the core Python toolchain; destructive `rm` / `sudo`
  are denied and still prompt outside that set.
- Adding a new documentation host requires editing both `.cursor/cli.json`
  (WebFetch) and `.cursor/sandbox.json` (networkPolicy), then updating this doc.
  Adding a Cursor MCP connector also requires `.cursor/mcp.json` and a matching
  `Mcp(<server>:*)` allowlist entry.
