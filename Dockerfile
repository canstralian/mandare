# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12.3
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

COPY . .

RUN python -m pip install -e .

# Persistent JSONL ledger lives here; mount a volume at this path in production.
# NOTE: Fly volume mounts replace this directory at runtime (often root-owned),
# so ownership is re-applied in scripts/docker-entrypoint.sh before dropping
# privileges — build-time chown alone is not sufficient.
RUN mkdir -p /app/data && chown appuser /app/data

COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

# Stay root for ENTRYPOINT so volume chown works; entrypoint drops to appuser.
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "rif_runtime.api:app", "--host", "0.0.0.0", "--port", "8000"]
