# Docker — RIF Runtime (governance MVP)

Pure-Python FastAPI image. No database and no Metasploit execution in the
container. Persistence is JSONL under `/app/data`. Threat-model honesty:
[SECURITY.md](SECURITY.md). Release notes: [RELEASE.md](RELEASE.md).

## Build

```bash
docker build -t rif-runtime:local .
# Equivalent (alias): docker build -f Dockerfile.prod -t rif-runtime:local .
```

Pin a digest for production registries after you push (`RELEASE.md` artifacts).

## Run (API keys + data volume)

Control-plane mutations require `RIF_CONTROL_PLANE_API_KEYS` (fail-closed).
Never bake keys into the image.

```bash
mkdir -p data
export RIF_CONTROL_PLANE_API_KEYS="replace-me-with-a-long-random-secret"

docker run --rm -p 8000:8000 \
  --read-only \
  --tmpfs /tmp \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  -e RIF_CONTROL_PLANE_API_KEYS \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/config:/app/config:ro" \
  rif-runtime:local
```

Restrict host permissions on `data/*.jsonl` (owner-only recommended).

## Compose

```bash
cp .env.example .env
# set RIF_CONTROL_PLANE_API_KEYS in .env

docker compose config          # validate
docker compose up --build -d --wait
curl -sf http://127.0.0.1:8000/health
docker compose -f docker-compose.prod.yml up -d --build
```

Default Compose file is `compose.yaml` (service name: `server`). There is no
parallel `docker-compose.yml` for the MVP path (avoids Compose dual-file
warnings). Entrypoint is `python -m uvicorn rif_runtime.api:app` **without**
`--reload`. Do not use `rif serve` as PID 1 in containers (reload breaks lifecycle).

## What this image is not

- Not an OS sandbox (seccomp/AppArmor profiles are deployer choices; not claimed by the package).
- Not a Postgres/Redis stack (aspirational compose leftovers were removed from the MVP path).
- Not a Metasploit runner (governance models intent only).
