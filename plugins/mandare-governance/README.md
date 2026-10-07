# mandare-governance

Status: **v0.1 host-enforcement adapter** for Claude Code. Canonical source for every repository
that consumes it (currently planned: Forge, Red Team Forge).

This plugin is a deterministic guard around Claude Code `tool.call` events. It is **not** a second
Mandare policy engine and **not** an authority source. Mandare's runtime, and each consumer's own
runtime, remain the authority for governed capabilities. The guard can stop an unsafe request
earlier; it can never make an otherwise unauthorized operation legal.

```text
model intent          != authority
host approval here    != runtime authority (Mandare, Red Team Forge, or any remote API)
tool availability     != authority
plugin installation   != trust
input hash            != credential
```

## Invariants

- Recognized external writes and destructive actions require a live `Approve once` answer to a
  prompt shown for that exact invocation.
- The prompt shows the whole invocation: a Bash command verbatim, any other tool as its name and
  canonical arguments. Control, zero-width and bidirectional characters are shown as escapes so the
  terminal cannot draw something other than what runs. An invocation longer than 4000 characters
  is denied rather than shown partially.
- Only `READ`, `LOCAL_WRITE`, `LOCAL_EXECUTION` and `NETWORK_READ` pass through. Any other value,
  including one the classifier was never written to return, is treated as unknown and denied.
- Approval is never cached or reused. A second call, identical or modified, gets a new prompt.
- Unknown built-in tools and unknown MCP operations are denied without prompting.
- A dismissed prompt, a free-text answer other than `Approve once`, or a session with nobody to ask
  (`-p`, CI) is a refusal.
- Governance failures fail closed (see below).
- Evidence stores hashes and decision metadata, never raw tool arguments or outputs.

## Effect classes

| Effect | Behavior |
| --- | --- |
| `READ` | pass through |
| `LOCAL_WRITE` | defer to normal Claude Code permissions |
| `LOCAL_EXECUTION` | defer to normal Claude Code permissions |
| `NETWORK_READ` | defer to normal Claude Code permissions |
| `EXTERNAL_WRITE` | require `Approve once` |
| `DESTRUCTIVE` | require `Approve once` |
| `UNKNOWN` | deny |

"Defer" means the call continues to the hooks beneath and to Claude Code's own permission rules,
which still decide. Approval here also defers: a deny rule beneath (for example a project's
`Bash(curl *)` deny) still refuses an approved call, and the evidence records
`execution.denied_downstream`.

MCP classification is verb-based on the operation name: destructive verbs win over write verbs,
which win over read verbs. An operation with no recognized verb is `UNKNOWN`. Add a reviewed
classification in `hooks/classify-effect.js` before relying on a new MCP operation or built-in tool.

Bash classification is conservative text matching, **not** a shell parser or sandbox. It covers
the common spellings of pushes (including force, `+refspec`, `:refspec`, `--delete`, `--mirror`),
`gh` writes, `gh api` non-GET calls, `curl` body flags and methods, `wget --post-*`, package
publishing, `kubectl`/`terraform` mutations and similar. Indirection (scripts, aliases, `eval`,
interpreters such as `python -c`) can evade it. Remote API permissions, branch protection,
credential scope, OS/container isolation and managed Claude Code policy remain stronger boundaries.

## Fail-closed behavior

Verified against the Claude Code 2.1.292 function-hooks declarations: a `tool.call` hook that
throws or outruns its budget is **skipped and the tool runs** unless its registration has a
`.catch`. The guard's `.catch` is `failClosed`, which answers in the guard's place:

| Situation | Answer |
| --- | --- |
| Guard failed before passing the call on (`throw`, `timeout`) | deny |
| Guard failed after the call already ran (`next.called`) | the call's settled result; a deny would undo nothing and misreport it |
| Re-entry: the call was raised beneath the guard's own in-flight call, so the guard is not run and cannot prompt | `READ`/local/network-read effects continue; `EXTERNAL_WRITE`, `DESTRUCTIVE`, `UNKNOWN` are denied |
| The handler's own logic throws | deny (the handler is written so it cannot throw; a throwing handler would leave the guard absent, which fails open) |

The hook budget (10 s) stops while `$` calls run, so a human taking time on the prompt does not time
the guard out.

## Trust boundaries and non-claims

- **Same-tier plugins.** Installed as a normal plugin, this guard runs in Claude Code's `user`
  tier. Other user-tier plugins can run before or after it. One that runs beneath it can rewrite a
  call after approval. One that handles `AskUserQuestion` can answer the approval prompt, because
  `$.ui.ask` is itself a `tool.call` of `AskUserQuestion` through every hook but the asking one. The
  guard is only as strong as the set of co-installed plugins.
- **Not mandatory at project scope.** A repository that enables this plugin in
  `.claude/settings.json` does not force it on anyone. A developer's `.claude/settings.local.json`
  (or a disabled install) turns it off. Only managed settings make a plugin mandatory, and only a
  managed `prepend`-tier deployment places it above user-tier plugins.
- **Cloud sessions.** Claude Code on the web does not add marketplaces that a repository declares in
  `extraKnownMarketplaces` (that needs the workspace trust dialog, which a cloud session never
  shows), so repository configuration alone does not load this guard there.
- **Re-entry denies.** If a guarded effect is raised beneath the guard's own call (for example by
  another hook's `$.tool.call`), it is denied rather than prompted. `[UNVERIFIED]` whether a
  subagent's own tool calls count as re-entry under an `Agent` call the guard passed through; if
  they do, subagents cannot obtain approval for guarded effects and are denied.
- **Evidence is not an audit log.** Guarded calls append a bounded (512 records), hash-linked suffix
  to the plugin store under `mandare.governance.evidence.v1`: effect, tool, input hash, decision,
  timestamp, previous-record hash. It supports local reconstruction and detects alteration within
  the retained suffix. A process with the user's permissions can replace or truncate it.

## Consuming this plugin

Consumers reference this plugin; they never copy `hooks/`. Repository-scope configuration:

```json
{
  "extraKnownMarketplaces": {
    "rif-runtime-marketplace": {
      "source": {
        "source": "github",
        "repo": "canstralian/mandare",
        "ref": "mandare-governance--v0.1.0",
        "sparsePaths": [".claude-plugin", "plugins/mandare-governance"]
      }
    }
  },
  "enabledPlugins": {
    "mandare-governance@rif-runtime-marketplace": true
  }
}
```

The relative-path source matters: Claude Code loads a plugin enabled only in project settings
without a per-user install step only when its marketplace entry is a relative path.

### Supply chain: what is and is not pinned

- A consumer pins the marketplace checkout to a `ref` (a branch or tag). Marketplace sources in
  settings do **not** accept a commit `sha`. A tag can be moved or deleted by anyone with push access
  to this repository, so a tag pin is a convention, not immutability.
- `plugin.json` sets `version`. Claude Code installs a new copy only when that string changes, so
  every release must bump `version` and be tagged `mandare-governance--v<version>` at the release
  commit.
- Background auto-update is off by default for this marketplace. A consumer receives new plugin code
  only when it changes its `ref` in a reviewed change, or when a user turns auto-update on.
- For a commit-exact pin, a consumer can instead declare an inline `settings` marketplace whose entry
  uses a `git-subdir` source with `sha`. Claude Code does not fetch such an external-source plugin
  from project settings alone; each user installs it once.

## Validate

Requires Claude Code 2.1.287 or later for function hooks. From this directory:

```bash
claude plugin validate .
claude plugin test
claude plugin eval . --case external-write-requires-approval --runs 1 --no-publish --allow-tools 'Bash(git push *)'
```

The eval is non-interactive: `$.ui.ask` has nobody to answer, so the guarded push must be denied.
It needs a working Claude Code sandbox backend (on Linux, `bubblewrap` and `socat`); without one
the eval harness refuses to run.

## Identity decision (v0.1)

- **Decision:** extract the guard into this plugin instead of renaming `rif-runtime`.
- **Evidence:** `rif-runtime` (source `./.claude`) bundles RIF Runtime operational skills that
  consumers should not inherit. Plugin renames migrate only through a `renames` map, and a
  marketplace rename has no migration path. No released version of `rif-runtime` contained the guard.
- **Identity:** `mandare-governance@rif-runtime-marketplace`.
- **Compatibility:** existing `rif-runtime@rif-runtime-marketplace` installs are unaffected.
- **Deferred:** renaming the marketplace would change every consumer's `enabledPlugins` key. If it
  ever happens, it needs a coordinated consumer change, because Claude Code has no marketplace
  rename mapping.
