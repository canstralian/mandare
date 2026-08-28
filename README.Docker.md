# Docker

This file supplements the main project documentation. For deployment/security decisions, see [`DEPLOYMENT.md`](DEPLOYMENT.md) and [`SECURITY.md`](SECURITY.md).

## Local development

```bash
docker compose up --build
```

The repository's Compose development configuration is `compose.yaml`.

The API is exposed on port `8000` by the supplied configuration.

## Build the image

```bash
docker build -t mandare:local .
```

The supplied Dockerfile runs the application as a non-root user. That is a useful baseline, not a complete container security profile.

## Production-oriented Compose

```bash
docker compose -f docker-compose.prod.yml up -d
```

Review the production Compose file and configure secrets, TLS, persistence, network boundaries, logging, and resource controls for the target environment before exposing the service.

## Important dependency note

The Dockerfile currently installs from the root-level `requirements.txt`, which is intentionally the unconstrained consumer dependency path. This differs from the hash-pinned dependency path used by locked CI jobs.

That distinction should be preserved in documentation: a successful Docker build is not equivalent to a reproducibly locked build.
