# spec/skill

Contract for the skill package format — the self-contained, versioned, testable
unit that packages a single capability (`SKILL.md` + `skill.yaml` + `scripts/` +
`references/` + `tests/`), per ADR-0008.

**Placeholder** — no schema yet. This runtime does not currently have a formal
skill package format; `.claude/skills/run-rif-runtime/SKILL.md` is the closest
existing example and should inform the first schema.

## Next slice
Define `skill_manifest.schema.json` for `skill.yaml`, based on the shape already
used in `.claude/skills/run-rif-runtime/`.
