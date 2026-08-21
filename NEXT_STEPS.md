# Next Steps

This file is intentionally short. The previous version duplicated an older greenfield roadmap, including commands, services, performance targets, Kubernetes plans, and capabilities that are not current repository behaviour.

## Current priority order

### 1. Preserve documentation/specification integrity

- keep implementation-backed docs synchronized with `src/` and workflows;
- keep specifications clearly labelled as specifications;
- inventory fixtures before cross-domain contract changes;
- avoid unsupported maturity, security, performance, or compliance claims.

### 2. Complete the open specification reviews

Cross-domain work involving identity, capability snapshots, replay, MCP, or provider egress should remain behind the existing specification-review process.

See [`docs/README.md`](docs/README.md) and [`spec/README.md`](spec/README.md).

### 3. Governed provider egress

Treat the provider-inference seam as specification work first:

```text
Decision
  -> Egress authorization
  -> Redaction
  -> Inference
  -> Advisory output
  -> Evidence
```

Do not enable provider access merely because a provider credential exists.

### 4. Evidence contract

Define which events are authoritative, what provenance means, what replay proves, how integrity is established, and how evidence is retained independently of the runtime host.

### 5. Release assurance

The next supply-chain hardening layer should address SBOMs, signed artefacts/provenance, reproducible builds, and consumer-side verification.

## Before any release

```text
- [ ] Current tests and relevant security checks verified
- [ ] Version/tag consistency verified
- [ ] API/CLI documentation current
- [ ] Security limitations documented
- [ ] Persistence/replay compatibility reviewed
- [ ] Open specification conflicts resolved or explicitly deferred
- [ ] Release notes distinguish shipped behaviour from planned work
```

## Current commands

See [`DEVELOPMENT.md`](DEVELOPMENT.md) and [`docs/cli-reference.md`](docs/cli-reference.md). Do not use historical `make` targets or CLI commands from old roadmap material without checking the current `Makefile`/`src/rif_runtime/cli.py`.

## Canonical roadmap

For longer-term planning, use [`docs/ROADMAP.md`](docs/ROADMAP.md). This file is an action-oriented companion, not a second roadmap.
