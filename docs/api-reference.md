# API Reference

> **Note:** The `/execute`, `/replay/{execution_id}`, `/evidence/{execution_id}`, and
> `/telemetry/{execution_id}` routes described here are **planned** and not yet implemented.
> The current API surface lives in `src/rif_runtime/api.py`; see `docs/API.md` for the
> existing routes. `GET /health` exists today but returns `environment` and `posture`
> fields in addition to `status`.

## Base URL

```text
/v1
```

## Execute

### POST /execute

Request:

```json
{
  "intent": "summarize evidence",
  "mode": "normal"
}
```

Response:

```json
{
  "execution_id": "exec_123",
  "status": "completed"
}
```

## Replay

### POST /replay/{execution_id}

## Evidence

### GET /evidence/{execution_id}

## Telemetry

### GET /telemetry/{execution_id}

## Health

### GET /health

Response:

```json
{
  "status": "ok"
}
```

## Errors

- 400 INVALID_REQUEST
- 401 UNAUTHORIZED
- 403 FORBIDDEN
- 409 CONFLICT
- 429 RATE_LIMITED
- 500 INTERNAL_ERROR
