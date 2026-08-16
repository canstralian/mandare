# RIF Research Baseline — 16 August 2026

**Status:** Baseline (supersedes the recurring daily research digest, now disabled)
**Scope:** External ecosystem observation feeding RIF architecture review
**Successor document:** `docs/spec-review-capability-snapshot-authority.md` (Track B)

---

## 0. How to read this document

This is a *research baseline*, not a specification and not a work plan. It records
what was observed in the external ecosystem and what that implies for RIF's
boundary. Nothing here is normative. The one question this cycle raised that is
genuinely a RIF contract question has been promoted into a specification review;
everything else is deliberately parked.

**Every external claim carries a verification status.** The originating brief was
assembled from sources that post-date reliable model knowledge, so each claim was
checked against a primary source before being allowed to influence a conclusion.

| Marker | Meaning |
| --- | --- |
| **[V]** | Verified against a primary or first-party source on 16 Aug 2026 |
| **[C]** | Verified, but the originating brief stated it incorrectly — correction recorded |
| **[U]** | Unverified. Not load-bearing for any conclusion in this document |

Claims marked **[U]** must not be cited in a specification decision without being
verified first.

---

## 1. MCP 2026-07-28 — the capability-contract question becomes real

**[V]** The MCP `2026-07-28` specification is final, following a release candidate
locked on 21 May 2026 and validated for roughly ten weeks before publication. It
follows `2024-11-05`, `2025-03-26`, `2025-06-18`, and `2025-11-25`.

**[V]** The changes that matter to RIF:

- **Stateless protocol core.** The `initialize`/`initialized` handshake and the
  protocol-level session are removed, along with the `Mcp-Session-Id` header.
  Every request is self-describing, carrying protocol version, client info, and
  client capabilities in its `_meta` parameter.
- **`server/discover`.** A new, *optional* RPC a client may call to learn a
  server's versions and capabilities up front. It is not required, and it is not
  a handshake.
- **Header-based routing.** `Mcp-Method` and `Mcp-Name` are required on
  streamable requests, so gateways, rate limiters, and WAFs can route and meter
  without parsing JSON bodies.
- **Cacheable list results.** Responses from `tools/list`, `prompts/list`,
  `resources/list`, and `resources/read` carry `ttlMs` **and `cacheScope`**, plus
  a deterministic order, so clients can cache tool catalogs.
- **Tasks demoted to an extension** (`io.modelcontextprotocol/tasks`).

> **Correction [C].** The originating brief cited only `ttlMs`. The spec defines
> **two** cache fields — `ttlMs` and `cacheScope`. `cacheScope` matters to RIF
> specifically, because a snapshot's shareability across actors or environments
> is a governance question, not just a caching one.

### The consequence for RIF

`ttlMs` is freshness metadata. It is not an implementation-stability guarantee,
and the specification makes no claim that a server's advertised capabilities
remain stable over time. Deterministic ordering exists to keep client-side caches
and upstream prompt caches stable across reconnects — it is a caching aid, not a
contract about behavior behind the catalog entry.

That yields the invariant this cycle actually produced:

> A run is authorized against a specific capability *observation*, not against an
> indefinitely stable remote server.

Which in turn implies a state machine:

```text
DISCOVER -> SNAPSHOT -> AUTHORIZE -> EXECUTE -> OBSERVE
```

with the requirement that a later catalog mutation must not silently mutate an
already-authorized run.

**This is the one item from this cycle promoted to specification review.** The
unresolved question — whether a tool call made after an external catalog change
remains governed by the original snapshot or forces a new authorization epoch —
is treated normatively in
`docs/spec-review-capability-snapshot-authority.md`.

**[V]** Relevant second-order note: the specification explicitly states that tool
descriptions and annotations "should be considered untrusted, unless obtained
from a trusted server." That is upstream language supporting RIF's existing
deny-by-default posture toward server-supplied metadata, and it bears directly on
§7 below.

---

## 2. Routing headers create a gateway insertion point

**[V]** Because `Mcp-Method` and `Mcp-Name` are required and body-independent, an
intermediary can authorize an MCP operation without parsing or trusting the JSON
body. That is architecturally significant for RIF: it means the enforcement point
does not have to live inside an agent framework.

```text
Agent -> MCP Gateway -> RIF policy / evidence boundary -> MCP Server -> Effect
```

> **Correction [C].** The originating brief stated that `2026-07-28` "standardizes
> W3C Trace Context propagation." **This is not supported.** The first-party
> release announcement does not mention W3C Trace Context, and the upstream
> tracking issue
> ([modelcontextprotocol#246](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/246))
> remains the live discussion for OpenTelemetry trace identifiers in the
> client→server protocol. Trace context over MCP today is *conventional
> OpenTelemetry practice on the HTTP transport*, not a protocol guarantee.
>
> **Why this matters:** any RIF gateway design must treat `traceparent` as
> best-effort correlation metadata it may have to originate itself, never as an
> identifier it can assume is present and trustworthy. A correlation design that
> assumed spec-guaranteed propagation would have been built on a false premise.

Parked prototype (not scheduled): a minimal gateway recording `run_id`,
`trace_id`, `Mcp-Method`, `Mcp-Name`, `capability_snapshot_id`, `policy_decision`,
and `effect_receipt_id`. Such a gateway should remain **non-authoritative for
history** until the ledger contract is settled — it can be an enforcement point
without becoming the source of truth.

---

## 3. Agent evaluation is becoming infrastructure

**[U]** AgentCompass reportedly separates benchmark, harness, and environment,
providing a fault-tolerant asynchronous runtime plus trajectory analysis across
20+ benchmarks and five capability dimensions.

**[U]** MobileJudgeBench reportedly evaluated 931 human-annotated trajectories
across six mobile-agent benchmarks, four agent models, and 68 apps, finding that
elaborate judge pipelines did not consistently beat simple baselines while the
underlying judge model strongly influenced results.

**[U]** AlphaEval reportedly argues conventional benchmarks diverge from
production because production requirements are implicit, inputs heterogeneous,
tasks long-horizon, and success standards evolving.

**[U]** Hugging Face's "Is it agentic enough?" work evaluates whole processes
rather than final answers, including how much work an agent does and how behavior
shifts across models and library revisions.

These four are recorded as **directional signal only**. None is verified, and
none is load-bearing. The architectural reading they collectively support —
already RIF's stated position — is:

> Evaluation should observe the runtime, not redefine it.

The durable consequence is a separation RIF should preserve in naming even before
it has an evaluation layer:

```text
ExecutionEvidence          EvaluationEvidence
├── path_hash              ├── evaluator_id
├── policy_receipts        ├── evaluator_model
├── effect_receipts        ├── evaluator_version
└── replay_result          ├── rubric_hash
                           ├── input_evidence_hash
                           └── score
```

A trajectory being deterministic does not make a judge score deterministic. The
judge is a second probabilistic subsystem, and its output must never become an
input to execution replay. RIF already holds this line implicitly; §5 of the spec
review makes it explicit.

**No evaluation subsystem is proposed for the runtime.** Benchmark decomposition
(scenario / harness / runtime / environment / policy / evidence / replay) is
recorded as future vocabulary, not a milestone.

---

## 4. ARD is discovery, not authorization

> **Correction [C].** The originating brief attributed Agentic Resource Discovery
> to Hugging Face. **ARD is a Google-published specification**, released
> 17 June 2026, with launch contributors including Cisco, Databricks, GitHub,
> GoDaddy, Google, Hugging Face, Microsoft, Nvidia, Salesforce, ServiceNow, and
> Snowflake. Hugging Face built the reference *Discover Tool*
> (`huggingface-hf-discover.hf.space`), wrapping Hub semantic search over Spaces,
> Skills, and MCP servers in the ARD envelope — an implementation, not the spec.

**[V]** ARD defines a static `ai-catalog.json` manifest at a well-known path plus
a registry API that indexes published catalogs and returns ranked matches to
natural-language queries.

**[V] — and this materially changes the priority.** ARD is at **v0.9**, and an
independent census the day after launch probed 39 domains, including all eleven
launch contributors, and found **none** serving a discoverable `ai-catalog.json`
at the specified well-known path. Adoption outside the two reference
implementations was not measurable.

**Consequence for RIF.** Discovery Evidence remains architecturally correct — the
model below is the right shape —

```text
ARD -> Discovery evidence -> Capability snapshot -> Authorization
```

— and specifically *not*:

```text
ARD -> Trusted capability
```

But an unadopted v0.9 spec does not justify a contract slice now. Discovery
Evidence is recorded as **deferred with a documented shape**, not scheduled. If
built later, it should preserve the candidate set so that selection is
reconstructable:

```text
query -> candidate set -> selection -> authorization
```

---

## 5. Harness/compute separation is externally validated

**[V]** OpenAI's Agents SDK update (15 April 2026) explicitly separates the agent
harness from the execution environment, with sandbox execution, snapshotting,
rehydration, and checkpointing — restoring agent state in a fresh container and
continuing from the last checkpoint if the original environment fails or expires.

**[V]** A stated motivation is **keeping credentials out of environments where
model-generated code executes**. This is a stronger argument than the
state-authority one alone, and it is the more useful framing for RIF: the
execution environment is not merely disposable, it is *untrusted with secrets*.

This validates RIF's shape:

```text
RIF (authoritative state, policy, evidence, replay)
        |
        v
disposable execution environment
```

It also reinforces a distinction RIF should write down before it accidentally
collapses:

```text
Replay   = reconstruct history
Recovery = continue execution
```

These must not become the same API. Promoted to the spec review as a normative
invariant.

**[V]** OpenAI announced on 3 June 2026 that Agent Builder and Evals wind down —
read-only 31 October 2026, shut down 30 November 2026 — with the Agents SDK
recommended for code-based workflows. The lesson for RIF is narrow and worth
stating plainly: **do not couple the evidence model to any vendor's visual
representation.** A portable runtime contract outlives an orchestration surface.

---

## 6. Compute backends stay replaceable

**[U]** vLLM v0.26.0 (reported 27 July 2026, 411 commits from 212 contributors,
with speculative decoding, LoRA, and NVFP4 support), llama.cpp's multi-platform
signed release stream, Gradio 6.21.0 (reported 29 July 2026, with MCP
resource/prompt support and OpenAPI exposure), and smolagents' release stream
(reported v1.26.0, with earlier v1.21.0 hardening `LocalPythonExecutor`) are all
recorded unverified.

They are not load-bearing. The architectural position they support is one RIF
already holds: the model layer should stay boring and swappable behind an
OpenAI-compatible interface. RIF should record `model_id`, `model_revision`,
`runtime_id`, and `runtime_revision` as execution-environment evidence, and
should not care how inference is internally scheduled.

Note that this is *evidence*, not *policy* — a reproducibility commitment about
the environment, not an authorization input.

---

## 7. Capability discovery is becoming an attack surface

**[U]** Reporting on "agent baiting" — malicious repositories posing as agent
skills or MCP servers, exploiting autonomous capability discovery — is recorded
as unverified, and the specific incident claims should be treated cautiously.

The **architectural** threat, however, needs no incident to justify it, and it is
corroborated by first-party language: the MCP specification itself instructs that
tool descriptions and annotations be treated as untrusted unless the server is
trusted (§1).

```text
Agent -> search -> malicious result -> install/connect -> execution
```

A discovery layer increases capability availability *and* capability-selection
attack surface simultaneously. This strengthens the case for recording discovery
query, registry, candidate set, selection, authorization, and execution as
**separate** events — because collapsing them destroys exactly the evidence
needed to investigate a bad selection.

It does **not**, given §4's adoption reality, justify building that now.

---

## 8. Meta-Harness — explicitly out of scope

**[U]** Work treating the agent harness itself as an artifact iteratively
optimized from complete histories (source, traces, evaluation scores).

Recorded for completeness. RIF could eventually evaluate runtime policies and
harness configurations rather than only agents. **This must not enter the
runtime.** It is noted here so that a future proposal citing it can be pointed at
this line.

---

## 9. The architectural delta from this cycle

```text
                   DISCOVERY
                       |
                       v
              Discovery Evidence
                       |
                       v
               Capability Snapshot
                       |
                       v
                  Agent Intent
                       |
                       v
            Authorization Context
                       |
                       v
                  Policy Gate
                       |
              +--------+--------+
              |                 |
             DENY             ALLOW
              |                 |
              v                 v
          Evidence           Effect
                                |
                                v
                         Effect Receipt
                                |
                                v
                          Observation
                                |
                                v
                             Ledger
                                |
                 +--------------+--------------+
                 v                             v
              Replay                      Evaluation
```

The addition versus the previous cycle is **Discovery Evidence preceding
Capability Snapshot**. Per §4, the box is drawn but not scheduled.

---

## 10. Boundary statement

This cycle does not justify a new RIF subsystem. It tightens the boundary:

| Layer | Role |
| --- | --- |
| ARD | discover |
| MCP | communicate |
| Agent framework | plan |
| **RIF** | **authorize + record + verify** |
| Sandbox | execute |
| OTel | observe |
| Evaluator | measure |
| vLLM / llama.cpp | compute |

RIF should not become another agent framework. Its defensible boundary is
authoritative execution state between untrusted planning and externally
observable effects — consistent with `docs/ROADMAP.md`'s north star and ADR-0008.

---

## 11. Disposition

| Item | Disposition |
| --- | --- |
| Capability snapshot semantics | **Promoted** — `docs/spec-review-capability-snapshot-authority.md` |
| Replay ≠ recovery invariant | **Promoted** — same document, §6 |
| Execution vs evaluation evidence | **Promoted as vocabulary** — same document, §5. No subsystem. |
| Discovery evidence schema | **Deferred** — shape recorded (§4); ARD v0.9 adoption does not justify a slice |
| MCP gateway interception | **Deferred** — viable insertion point (§2); blocked on snapshot contract |
| Benchmark/harness decomposition | **Deferred** — vocabulary only (§3) |
| Execution-environment evidence fields | **Deferred** — recorded (§6), evidence not policy |
| Meta-Harness | **Rejected for the runtime** (§8) |
| `trajectory_cost` metric | **Not adopted** — no current RIF consumer |

### Verification debt

Claims marked **[U]** above — AgentCompass, MobileJudgeBench, AlphaEval, the
Hugging Face evaluation post, vLLM/llama.cpp/Gradio/smolagents versions, and the
agent-baiting reporting — remain unverified. None gates a promoted item. Any
future proposal that depends on one must verify it against a primary source
first.

## 12. Sources consulted (16 Aug 2026)

Listed so a reviewer can re-check any **[V]**/**[C]** marker directly, rather
than taking this document's word for it. Two tiers, marked explicitly — full
first-party text retrieval is stronger evidence than a search-engine summary
of one, and this baseline's own discipline (§0) requires saying which is which:

**Retrieved directly (full first-party text):**
- MCP `2026-07-28` release announcement —
  <https://blog.modelcontextprotocol.io/posts/2026-07-28/>
  (§1: stateless core, `server/discover`, `Mcp-Method`/`Mcp-Name`, `ttlMs` +
  `cacheScope`, deterministic ordering, Tasks extension)
- MCP `2026-07-28` specification index —
  <https://modelcontextprotocol.io/specification/2026-07-28>
  (§1: base protocol, extensions overview, security/trust principles)

**Consulted via search-engine summary (not independently fetched in full —
verify directly before citing further):**
- W3C Trace Context absence from the MCP spec — upstream tracking issue
  <https://github.com/modelcontextprotocol/modelcontextprotocol/issues/246>
  (§2 correction)
- ARD provenance and adoption — Google's ARD announcement and Hugging Face's
  Discover Tool post, <https://huggingface.co/blog/agentic-resource-discovery-launch>,
  plus third-party coverage of the launch and the post-launch adoption census
  (§4 correction)
- OpenAI Agents SDK harness/sandbox separation —
  <https://openai.com/index/the-next-evolution-of-the-agents-sdk/> (§5)
- OpenAI Agent Builder/Evals wind-down timeline — OpenAI's own announcement,
  corroborated by third-party migration-guide coverage (§5)

Every **[U]**-marked claim (§3, §6, §7) was **not** checked against any
source this cycle and is not included above.
