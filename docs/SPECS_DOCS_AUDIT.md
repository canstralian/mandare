# Specification & Documentation Audit

**Scope:** `spec/`, `contracts/`, `docs/`, and root-level `*.md`, audited against
`src/rif_runtime/`, `supabase/migrations/`, `config/`, and `tests/`.

**Re-verified against `main` at `9df47d4`** (2026-08-22). The first pass of this
audit ran against `87498bd`; the large documentation overhaul that landed on `main`
in between resolved most of what it found. Every finding below has been re-checked
against the current tree — resolved items are recorded as resolved rather than
deleted, so the fixes are traceable.

**Method:** every normative claim that names a module, route, identifier, table, or
constant was checked against the referenced source.

**Standing principle:** per `CLAUDE.md` and `spec/README.md`,
`src/rif_runtime/api.py` is the source of truth for the API surface, and `spec/` is
normative for contracts. Where a doc contradicts code, the doc is the defect —
*unless* the doc is a spec, in which case the finding is that the implementation has
not caught up and the spec must say so rather than claim conformance.

---

## Open findings

| # | Finding | Severity |
|---|---|---|
| H3 | `spec/` schemas are byte-identical duplicates of `contracts/rif_familiar/`, and only the `contracts/` copies are tested | High |
| H5 | `spec/mcp/SPEC.md` gates on a `destructive` capability class the named classifier cannot return | High |
| M1 | `spec/mcp/SPEC.md` §4 lane order does not mirror `MetasploitGovernor.evaluate()` as claimed | Medium |
| M2 | Deny-reason identifiers differ between spec (`mcp.*`) and implementation (`msf.*`) | Medium |
| M3 | Capability-token TTL: spec says 300 s, code defaults to 600 s in both call sites | Medium |
| M4 | `POST /v1/runs` is the one route documented nowhere | Medium |
| M7 | Identity-spine spec review cites three nonexistent ADRs and skips a section | Medium |
| H2 | ADR numbering is split across two conventions with 0001 and 0009–0025 absent | Medium (was High) |
| M6 | Root-level duplicates of `docs/` files persist | Low (was Medium) |
| L1 | `tem]` junk file at repo root | Low |

### H3. `spec/` duplicates `contracts/`, and the copies are untested

ADR-0008:53-54 states: "Existing `contracts/rif_familiar/` schemas are the seed for
`spec/capability/` and `spec/skill/` — **migrate rather than duplicate**."

What shipped is duplication. All three schemas are byte-identical between the two
trees (verified by `diff`; all three report no differences):

- `contracts/rif_familiar/capability_manifest.schema.json` ≡ `spec/capability/…`
- `contracts/rif_familiar/observation_event.schema.json` ≡ `spec/evidence/…`
- `contracts/rif_familiar/posture_decision.schema.json` ≡ `spec/governance/…`

The divergence risk is not hypothetical: `tests/test_rif_familiar_contracts.py:9`
binds validation to `ROOT / "contracts" / "rif_familiar"` only. **The `spec/` copies
have no test coverage at all** and can drift from the tested originals silently.

Note also that ADR-0008 names `spec/capability/` and `spec/skill/` as the seed
targets; the actual seeding went to `capability/`, `governance/`, and `evidence/`,
while `skill/` remains a placeholder.

**Recommendation (smallest sufficient fix):** parametrize
`tests/test_rif_familiar_contracts.py` over both roots, or add a test asserting the
two trees are byte-identical, so the duplication cannot rot unobserved. Then settle
the re-export-vs-retire question.

### H5. The MCP hard gate keys off a capability class that cannot be produced

`spec/mcp/SPEC.md` §5 defines a three-class taxonomy — `read_only`,
`consequential`, `destructive` — and names the implementation normative:
"Classification reuses the existing `capabilities.classify` / `is_severe` machinery
(`src/rif_runtime/mcp/capabilities.py`) … new servers extend the catalog, they do
not fork the classifier."

`src/rif_runtime/mcp/capabilities.py:22-27` defines:

```python
class CapabilityClass(StrEnum):
    read_only = "read_only"
    consequential = "consequential"
    unknown = "unknown"
```

There is **no `destructive` member**, and `classify()` (lines 91-97) can only return
one of those three. Severity is a separate, orthogonal predicate, `is_severe()`
(lines 100-101), backed by `SEVERE_CAPABILITIES`.

This matters because the spec's security centre of gravity hangs off that class.
§4.7 ("A `destructive` capability … MUST pass the full §6 hard gate") and §6 (the
seven-check gate) are conditioned on a classification the named normative classifier
can never return, and §11's GREENLIGHT criteria make the destructive gate a named
pass/fail criterion. Read literally, the gate is unreachable.

The `unknown` case is also unmodelled: C7 requires that "an unclassified or
unregistered tool is denied," and the implementation does deny `unknown` by routing
it through the consequential path — but the spec's three-class model has no slot
for it.

**Recommendation:** decide whether `destructive` becomes a real fourth
`CapabilityClass` member (with `SEVERE_CAPABILITIES` promoted into it), or whether
the spec defines destructive as `consequential ∧ is_severe()`. Either is defensible;
the current text asserts a mapping that does not exist. Tracked as **OD-7** in
`spec/mcp/SPEC.md` §14. This is a design decision for the spec owner, so it is
flagged rather than resolved here.

### M1. §4's lane order does not mirror the implementation it cites

`spec/mcp/SPEC.md` §4 states the ordered lanes "mirror `MetasploitGovernor.evaluate()`
and MUST be preserved." Comparing directly:

| Spec §4 lane | `MetasploitGovernor.evaluate()` |
|---|---|
| §4.1 posture gate | `metasploit.py:249` — same position |
| §4.2 egress gate | **not in the governor at all** — the egress check lives in `PolicyEngine.evaluate()` (`policy.py:76-85`), a different component on a different call path |
| §4.3 injection quarantine | `metasploit.py:261` — but *second*, not third |
| §4.4 read-only fast-path | `metasploit.py:278` — third, not fourth |
| §4.5 consequential authority | split across three `GovernanceMode` lanes (`read_only_firewall`, `shadow`, `lab_broker`, lines 290-314) that §4 does not mention |

The `GovernanceMode` enum is the governor's central structuring concept and is
absent from the spec entirely. The spec is also broader on §4.3's scan surface (it
adds tool descriptions, server metadata, and returned tool results;
`scan_for_injection` covers only `intent.text`, `intent.untrusted_context`, and
recursed `params`).

Framework-level generalization is legitimate — but "mirrors … MUST be preserved"
asserts present-tense conformance that does not hold. §14 now records the delta;
the §4 wording itself still needs an owner's edit.

### M2. Deny-reason identifiers differ between spec and implementation

The spec's reason strings use an `mcp.*` namespace; the implementation emits `msf.*`.
Only two of the spec's identifiers exist in code as written:

| Spec | Code | Status |
|---|---|---|
| `posture.locked` | `posture.locked` (`metasploit.py:256`) | match |
| `mcp.egress.disabled` | `mcp.egress.disabled` (`policy.py:84`) | match |
| `mcp.injection.quarantined` | `msf.injection.quarantined` | differs |
| `mcp.capability.read_only` | `msf.capability.read_only` | differs |
| `mcp.authority.absent` | `msf.capability.execution_absent` / `msf.broker.approval_absent` | differs |
| `mcp.gate.*` (7 reasons, §6) | `msf.broker.*` | differs |

These strings are persisted into `EvidenceEvent.matched_rule` and are the audit
trail's primary index, so an undocumented rename is a replay hazard: a query written
against the spec finds nothing in the log. §14 now carries the full mapping table;
whether to rename (breaking historical evidence) or keep `msf.*` is **OD-8**.

### M3. Capability-token TTL disagrees with the implementation

`spec/mcp/SPEC.md` §6.3 — "Default TTL **300 s**; authority is time-bound."

Both call sites default to 600 s:
- `src/rif_runtime/mcp/metasploit.py:219` — `ttl_seconds: int = 600`
- `src/rif_runtime/api.py:195` — `int(payload.get("ttl_seconds", 600))`

A doubled default on a security-critical time bound deserves a deliberate
reconciliation: either the spec's 300 s is the intent and the code should tighten, or
the spec should record 600 s. Tracked as **OD-9**.

The spec is correct that TTL is enforced (`metasploit.py:350`) and that the intent
hash excludes free-text fields (`intent_hash()` covers `tool`, `capability`,
`target`, `scope_id`, `params`, omitting `text` / `untrusted_context`). Single-use
`token_id` enforcement (§6.4) remains unimplemented — the spec is candid about this
under OD-3.

### M4. `POST /v1/runs` is documented nowhere

`docs/API.md` has been rewritten and is now accurate: it covers 19 of the 20 routes
in `api.py`, with an auth column, and the nonexistent `POST /v1/runtime/reset-posture`
is gone. `CLAUDE.md`'s route block, previously malformed (literal `\n` escapes on one
line), is also fixed.

The one gap left: **`POST /v1/runs`** (`api.py:235`) appears in no document —
verified by checking each route string in `api.py` against `docs/API.md`. It is also
the only route authenticated by Supabase JWT identity (`IdentityId`) rather than
`ControlPlaneAuth`, which is a security-relevant distinction no document records.

### M7. The identity-spine spec review cites ADRs that do not exist

`docs/spec-review-identity-spine-migration.md` is normative in tone ("Governs:
ADR-0010", "binding on all future migrations") and cites **ADR-0010, ADR-0012, and
ADR-0015** nine times. None exists in `docs/` or `docs/adr/`. Its ratification
checklist (§11) requires "ADR-0010 is updated to reference this document as its
implementation authority," which cannot be satisfied.

The document also jumps from §11 to §13 — there is no §12.

One time-sensitive item: §7 scopes the `execution_id` deprecation window as
`v0.2.x → v0.3.0`, with input aliases "removed at `v0.3.0`." The code is already
clean — `execution_id` has zero occurrences in `src/` — so the deprecation appears
complete in practice and only the checklist is stale.

### H2. ADR numbering (downgraded from High)

The original collision is gone: `rif-runtime-adrs.zip` was deleted from `main`,
removing the second series that reused numbers 0001–0008 for entirely different
decisions. What remains is a milder inconsistency:

- `docs/adr-000N-*.md` — lowercase, flat in `docs/`, numbers 0002–0008
- `docs/adr/ADR-002N-*.md` — uppercase, in a subdirectory, numbers 0026–0027
- **ADR-0001 no longer exists anywhere.** It was only ever present as the two
  root `nse-*.md` copies and inside the deleted zip; both are now gone.
- 0009–0025 are unaccounted for, including the ADR-0010/0012/0015 that M7 depends on.

**Recommendation:** settle on one convention and location, and add an index ADR
recording what 0001 and 0009–0025 were, so M7's dangling references can be resolved.

### M6. Root-level duplicates (downgraded from Medium)

`cli-reference.md`, `mcp-integration-guide.md`, and `ARCHITECTURE.md` still exist
both at root and under `docs/`, with differing content (root `ARCHITECTURE.md` is
184 lines against `docs/ARCHITECTURE.md`'s 9). `release-engineering-guide.md` exists
only at root.

The accuracy problem is fixed — root `cli-reference.md` now carries its own note that
`rif execute` / `evidence` / `telemetry` / `validate` / `policy` "are
historical/planned and are not current commands," matching the real command set
(`serve`, `check`, `replay`, `msf-check`). What is left is ordinary duplication:
two files with the same name that must be maintained in step.

### L1. `tem]`

A 6.9 KB file at repo root containing ANSI-escaped terminal output from `bat`
rendering an old `pyproject.toml` (showing `version = "0.2.0"`). Plainly the residue
of a shell redirect typo. Safe to delete.

---

## Resolved since the first pass

These were findings against `87498bd` and are fixed on `main` at `9df47d4`.

| # | Finding | How it was resolved |
|---|---|---|
| H1 | `docs/DATA_MODEL.md` claimed to be the schema source of truth while sharing zero tables with the only shipped migration | Rewritten as "Data Model **Proposal** — Status: draft design," explicitly "**not** the schema of the current default runtime" and not to be used as evidence of implementation |
| H4 | Root `ARCHITECTURE.md` documented eleven modules absent from `src/` | Rewritten; no phantom module citations remain |
| L2 | ADR-0001 duplicated at root under machine-generated names (`nse-*.md`) | Both files deleted (see H2 — ADR-0001 now absent entirely) |
| L3 | Two `.zip` archives of documentation committed at root | `rif-runtime-adrs.zip` and `rif-runtime-specification-docs.zip` both deleted |
| L4 | Twelve nonexistent paths cited across `CONTRIBUTING.md`, `DEVELOPMENT.md`, `NEXT_STEPS.md`, `SECURITY.md`, `DEPLOYMENT.md` | All stale references removed in the docs overhaul; re-scanned, and the only file still naming them is this audit |
| L6 | `notebooklm/` was an unmaintained fork of `docs/` frozen at v0.2.x | The forked `docs/` subtree deleted |
| L7 | `DATA_MODEL.md` typed `trust_tier` as T0–T3 while `spec/mcp/SPEC.md` defines T0–T4 | The `trust_tier` row is gone in the rewritten document |
| — | `CLAUDE.md`'s API-surface block was malformed (literal `\n` escapes) | Fixed in the `CLAUDE.md` rewrite |

## Suggested sequencing

1. **H3's test gap** — smallest change, removes an active silent-drift risk.
2. **H5 destructive-class decision** (OD-7) — unblocks the MCP conformance story.
3. **M2 / M3** (OD-8, OD-9) — namespace and TTL; both are one-line decisions with
   downstream effects on replay and on token lifetime.
4. **H2 / M7** — renumber the ADRs and resolve the dangling ADR-0010/0012/0015.
5. **M4 / M6 / L1** — mechanical and independently mergeable.
