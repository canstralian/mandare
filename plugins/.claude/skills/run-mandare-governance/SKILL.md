---
name: run-mandare-governance
description: Run, drive and smoke-test the mandare-governance Claude Code plugin in a real headless Claude Code session. Use when asked to run or verify the governance plugin live, check whether a command would be denied or allowed, reproduce a classifier bypass end to end, or confirm a classifier/hook change works outside `claude plugin test`.
---

`mandare-governance` (`plugins/mandare-governance/`) is a `tool.call` hook module, so its
surface is a running Claude Code session. The driver `smoke.sh` launches headless `claude -p`
sessions with the plugin loaded via `--plugin-dir`. It reads the actual Bash tool result
from `stream-json`, not the model's summary. All paths below are relative to the repo root. The skill lives under
`plugins/.claude/` so neither marketplace plugin (`.claude/`, `plugins/mandare-governance/`) ships it.

## Prerequisites

- The `claude` CLI on `PATH`. Checked with 2.1.306; CI pins 2.1.292 for `plugin test`.
- `git`, `python3`, and `gh` (used only as a string; nothing reaches GitHub).

## Run (agent path)

Full case table, about 1 minute, exits non-zero on any FAIL:

```bash
plugins/.claude/skills/run-mandare-governance/smoke.sh
```

The table checks:

- A control push without the plugin succeeds.
- These are each denied with the right effect: `git -C … push`, `git -c … push --force`, a
  push wrapped in `bash -c`, and `gh repo delete`.
- A local read passes.
- The throwaway remote is unchanged.
- The evidence ledger has 4 denials in one linked hash chain, with no command text stored.

Ask how the live plugin treats one command:

```bash
plugins/.claude/skills/run-mandare-governance/smoke.sh run "gh workflow run deploy.yml -R o/r"
# exact  plugins=mandare-governance  <tool_use_error>Mandare denied EXTERNAL_WRITE: this exact invocation was not approved.</tool_use_error>
```

Each output line has three fields:

- `exact` means the model ran the command verbatim, as its only tool call. Any other value
  means the result says nothing about the plugin; re-run.
- `plugins=` lists the non-builtin plugins loaded in that session.
- The last field is the raw tool result.

The work directory (bare remote, repo, `cfg/` with the plugin store) is printed at the end.
Set `SMOKE_DIR=<dir>` to choose it; it must be new or empty, or the driver exits 2.

## Test (unit level)

```bash
claude plugin test plugins/mandare-governance
claude plugin validate plugins/mandare-governance
```

## Gotchas

- **Isolate the config, or the result is meaningless.** Without a fresh `CLAUDE_CONFIG_DIR`,
  plugins synced into this host's `~/.claude` load as well. On this container an agentic-sdlc
  plugin blocks `git push` on its own ("Human gate (Agentic SDLC invariant 4)"), so a denial
  is not evidence of Mandare. The driver blanks `CLAUDE_CODE_SYNC_PLUGINS`/`_SKILLS` and
  prints `plugins=` so you can see what was loaded. Authentication still works with a fresh
  config dir, because this environment authenticates through `ANTHROPIC_BASE_URL`.
- **Headless only ever reaches the deny branch.** In `-p` nobody can answer `Approve once`,
  so every guarded call ends `refused_or_unattended`. The approve-then-run-once path cannot
  be driven here; it is covered only by `claude plugin test`.
- **No MCP servers in the isolated config.** MCP `UNKNOWN` → prompt cannot be observed with
  this driver. Use `claude plugin test` for it.
- **Don't add `rm` cases.** The host's own removal safety check refuses `rm -r`/`rm -rf`
  commands, even on scratch paths. The refusal comes from the outer harness, not from
  Mandare, so it would muddy the result.
- **Indirection passes by design.** `sh push.sh` wrapping a push runs and moves the remote.
  This is the README's stated non-claim, not a regression.
- **The control push prints `fatal: expected 'acknowledgments', received 'packfile'`.**
  That comes from a local bare remote under this git (2.43). The push still lands
  (`main -> main`).
- **Run sessions one at a time when checking the ledger.** Appends are serialized only
  within one process, so concurrent sessions are a documented gap.

## Troubleshooting

- **The `plugins=` field lists more than `mandare-governance`.** The config wasn't isolated.
  Run through `smoke.sh`, not bare `claude -p`.
- **`NOT-EXACT(n calls)` or `<command not run verbatim>`.** The model rewrote the command or
  made extra calls. Re-run, or simplify the command's quoting.
