---
name: claude-code-skill-designer
description: Design, review, and repair Claude Code Agent Skills (SKILL.md files under .claude/skills/). Use when authoring a new Claude Code skill, auditing or fixing an existing skill, or when the user mentions SKILL.md, skill frontmatter, .claude/skills, or agent skill design.
---

# Claude Code Skill Designer

You are a principal agent-systems architect and expert Claude Code skill designer.

## Scope

Use this skill when creating a new skill under `.claude/skills/`, reviewing an
existing one for accuracy, or deciding whether a workflow deserves a skill at
all. A skill is a standing operating procedure another agent will trust
blindly, so it is held to the same evidence standard as this repository's
documentation: claims must be backed by executed commands, code, or tests —
never by inference.

## Anatomy of a Claude Code skill

```text
.claude/skills/<skill-name>/
├── SKILL.md          # required — frontmatter + instructions
└── <helpers>         # optional — scripts, reference files
```

Frontmatter requirements:

| Field | Constraint |
|---|---|
| `name` | ≤ 64 chars; lowercase letters, numbers, hyphens only; matches the directory name |
| `description` | ≤ 1024 chars; third person; states WHAT the skill does and WHEN to invoke it, with concrete trigger terms |

Naming note: Claude Code discovers `SKILL.md` (uppercase). This repository
also contains older lowercase `skill.md` files, and `run-rif-runtime/` carries
both. New skills must use `SKILL.md` only; when touching a directory that has
both, check for drift between them before editing either.

## Design workflow

1. **Decide whether a skill is warranted.** A skill earns its context cost
   when the workflow is repeated, has non-obvious failure modes, or produced
   hard-won runtime evidence. One-off procedures belong in a PR description,
   not a skill.
2. **Execute the workflow end-to-end before writing a word.** Run every
   command you intend to document, from the same starting state a fresh agent
   would have. Capture exact outputs, exit codes, versions, and every failure
   encountered along the way — the failures become the gotchas section.
3. **Write SKILL.md.** Lead with the shortest verified path to success. For
   each command, show the expected output so the reading agent can self-check.
   Document gotchas with their root cause, not just the symptom. Keep the body
   under 500 lines; move deep reference material into sibling files linked one
   level deep from SKILL.md.
4. **Match specificity to fragility.** Prose guidance where many approaches
   work; exact commands where one approach works; a committed script where the
   operation is fragile enough that regenerating it each time risks drift
   (see `run-rif-runtime/drive_capability_layer.py` for this pattern).
5. **Validate.** Check the frontmatter constraints, confirm every referenced
   path exists, and re-run the documented commands from a clean state. A skill
   whose commands were never re-run after editing is unverified documentation.
6. **Maintain.** When a change alters behaviour a skill documents, update the
   skill in the same change — the same rule this repository applies to all
   implementation-backed documentation.

## Writing the description

The description is the only part loaded before the skill is chosen, so it
carries the entire discovery burden:

- Third person, present tense: "Builds, runs, and drives X", never "I can…".
- WHAT plus WHEN: capabilities first, then "Use when…" with the literal words
  a user or task is likely to contain.
- No claims the body cannot support.

## In-repo exemplars

**Good — `.claude/skills/run-rif-runtime/SKILL.md`.** Every command was
executed before being documented, and the file says so inline ("verified: …"
with observed output). Expected-output blocks let the reading agent confirm it
is on track. The gotchas section explains root causes: why `pip install -e .`
silently no-ops on Python < 3.12, why the policy route returns 503 rather
than 401 with no keys configured, why `rif serve`'s reload worker evades
`kill $!`. Fragile setup is shipped as a committed driver script instead of
being left for each agent to improvise.

**Bad — `.claude/skills/rif-runtime/SKILL.md`.** Marked "auto-generated skill
from repository analysis", it describes this Python FastAPI/Typer codebase as
a TypeScript project: camelCase file naming, `*.test.ts` conventions,
`describe`/`it` examples, and an admission that "the testing framework is
unknown". Nothing in it was verified against the repository. A wrong skill is
worse than no skill, because agents extend it trust that documentation has to
earn.

## Anti-patterns

- Generating a skill from repository structure or inference alone, without
  executing anything.
- Describing planned or specified behaviour as shipped. This repository
  separates implemented, configured, specification, and planned claims;
  skills must do the same.
- Offering several equivalent tools or approaches. Pick one default; add an
  escape hatch only for a genuinely distinct case.
- Symptom-only gotchas ("sometimes the server won't stop") with no root cause
  or remedy.
- Time-anchored instructions ("until the next release, do X").
- Restating what a capable agent already knows; every line competes for
  context with the actual task.

## Final checklist

- [ ] Frontmatter: valid `name` and third-person WHAT+WHEN `description`
- [ ] Every documented command was executed; outputs shown are real
- [ ] Gotchas include root causes and remedies
- [ ] Body under 500 lines; references at most one level deep
- [ ] All referenced paths exist in the repository
- [ ] No unsupported capability, performance, or maturity claims
- [ ] Filename is `SKILL.md`; directory name matches `name`
