# Deployment Guide

This repository supplies a local Docker Compose deployment and a production-oriented single-host Compose file. It does **not** currently ship a supported Kubernetes distribution or a turnkey multi-node control plane.

## Development

```bash
docker compose up --build
```

This uses `compose.yaml` and is intended for local development. Do not expose it directly to an untrusted network.

## Production-oriented single host

The repository provides:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Inspect `docker-compose.prod.yml` before deployment. Treat it as a baseline, not as proof that a deployment is enterprise-ready.

## Pre-deployment checklist

- [ ] Pin the exact application version/image being deployed.
- [ ] Review `SECURITY.md` and the current threat model.
- [ ] Configure `RIF_CONTROL_PLANE_API_KEYS` through a managed secret mechanism.
- [ ] Put the API behind trusted TLS termination and an appropriate network boundary.
- [ ] Restrict administrative access to control-plane endpoints.
- [ ] Define the persistence directory and backup/restore procedure.
- [ ] Decide retention and privacy requirements for decision/evidence data.
- [ ] Configure centralized logs and alerting.
- [ ] Restrict outbound network access to what the deployment actually needs.
- [ ] Verify the release and CI/security status for the exact commit or tag.
- [ ] Exercise recovery before relying on persisted state operationally.

## Configuration

Mandare configuration is primarily file- and environment-driven. Review `rif.toml`, `config/`, and the runtime configuration models before changing defaults.

Control-plane authentication uses:

```text
RIF_CONTROL_PLANE_API_KEYS=<comma-separated API keys>
```

Optional Supabase-backed run/evidence features use the environment variables documented in `src/mandare/integrations/supabase.py`. Supabase is optional and is not the default local persistence mechanism.

## Persistence and backups

The default runtime persists state as local JSON/JSONL files under the configured data directory. This is simple and inspectable, but it is not a distributed storage system.

For an operational deployment:

1. place the data directory on managed persistent storage;
2. define backup frequency and retention;
3. test restore into an isolated environment;
4. verify that restored decision history produces the expected replayed posture/graph state;
5. protect backups independently from the runtime host.

Do not describe JSONL as an immutable or tamper-proof ledger. Filesystem access can modify it.

## TLS and networking

The application listens for HTTP traffic. Production deployments should terminate TLS at a trusted reverse proxy/load balancer or otherwise provide equivalent transport protection.

Restrict inbound access to the required API surface. Restrict outbound access according to the actual capabilities and integrations enabled in the deployment.

Mandare's application-level policy checks are not a substitute for network-layer egress controls.

## Container security

The supplied Dockerfile runs the application as a non-root user. Additional hardening should be applied at deployment time according to the threat model, including where appropriate:

- read-only root filesystem;
- dropped Linux capabilities;
- `no-new-privileges`;
- seccomp/AppArmor/SELinux policy;
- CPU, memory, process, and file-descriptor limits;
- restricted network egress;
- managed image provenance and scanning.

These controls are deployment choices unless explicitly present in the supplied deployment configuration.

## Health and observability

The application exposes:

```bash
curl http://127.0.0.1:8000/health
```

The repository also exposes telemetry and persistence summaries through the API. It does not currently ship a complete Prometheus/Jaeger observability stack, so external monitoring must be provided by the deployment environment if required.

## Upgrades and rollback

The release workflow validates that a Git tag matches the package version, runs the repository's release verification commands, builds Python distributions, and publishes a GitHub Release.

For operational upgrades:

1. record the exact current commit/tag;
2. back up persistent state;
3. deploy the new version in a controlled environment;
4. run health, policy, replay, and relevant integration checks;
5. observe the deployment before increasing exposure;
6. retain a tested rollback path to the previous version.

The repository does not currently provide a built-in database migration framework or blue/green deployment controller.

## High availability and scaling

Do not assume horizontal scaling is safe merely because the HTTP layer is stateless. Runtime posture and local JSONL persistence introduce shared-state concerns.

Multi-instance deployment requires an explicit design for:

- shared or coordinated persistence;
- write ordering and concurrency;
- policy/configuration consistency;
- replay semantics;
- backup and recovery;
- authentication and secret rotation.

No throughput or request-per-second target is asserted here because the repository does not currently provide a maintained performance benchmark.

## Disaster recovery

A minimal recovery exercise should demonstrate:

```text
backup
  -> restore into isolated data directory
  -> start runtime
  -> replay persisted decisions
  -> inspect recovered posture/graph
  -> verify health and policy evaluation
```

Record the result of that exercise with the deployment documentation rather than treating the existence of a backup script as evidence of recoverability.

## Security boundary

A deployment is not enterprise-grade merely because it runs the supplied container. Enterprise assurance requires the surrounding identity, network, secret, storage, observability, vulnerability-management, backup, and incident-response controls to be designed and tested for the intended environment.

See [`SECURITY.md`](SECURITY.md) for the application-level security model and its explicit limitations.
