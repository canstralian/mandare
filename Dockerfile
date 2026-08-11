# syntax=docker/dockerfile:1
#
# RIF Runtime — governance MVP image (pure-Python FastAPI).
# Prefer: python -m uvicorn rif_runtime.api:app (no --reload) for PID/lifecycle.
# Do not claim OS sandboxing; see SECURITY.md.

ARG PYTHON_VERSION=3.12.3

# ---------------------------------------------------------------------------
# Builder: install deps + package into an isolated venv (layer-cache friendly)
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Dependency layer first (cache hits when only app code changes).
COPY requirements.txt pyproject.toml README.md ./
COPY src ./src

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -U pip \
    && python -m pip install -r requirements.txt \
    && python -m pip install --no-deps .

# ---------------------------------------------------------------------------
# Runtime: non-root, minimal surface, signal-friendly uvicorn PID 1
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Working directory is /app so relative data/ and config/ resolve as in CLI.
    RIF_DATA_DIR=data \
    RIF_CONFIG_DIR=config

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser \
    && mkdir -p /app/data /app/config \
    && chown -R appuser:appuser /app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Environment profiles (required at startup). Seed policies are created by
# PolicyStore defaults if data/policies.json is absent on the volume.
COPY --chown=appuser:appuser config/environments.yaml /app/config/environments.yaml
COPY --chown=appuser:appuser rif.toml /app/rif.toml

USER appuser

EXPOSE 8000

# No curl in slim — use stdlib. /health is unauthenticated by design.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# uvicorn as PID 1 forwards SIGTERM for clean shutdown (avoid rif serve --reload).
CMD ["python", "-m", "uvicorn", "rif_runtime.api:app", "--host", "0.0.0.0", "--port", "8000"]
