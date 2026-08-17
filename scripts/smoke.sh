#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8000}"
API_KEY="${RIF_CONTROL_PLANE_API_KEYS:-}"
API_KEY="${API_KEY%%,*}"
if [[ -z "${API_KEY}" ]]; then
  echo "RIF_CONTROL_PLANE_API_KEYS must be set (comma-separated); smoke uses the first key" >&2
  exit 1
fi
AUTH=(-H "X-API-Key: ${API_KEY}")
curl -fsS "$BASE/health"; echo
curl -fsS "$BASE/v1/environments"; echo
curl -fsS "$BASE/v1/audit"; echo
curl -fsS -X POST "$BASE/v1/policy/evaluate" -H 'content-type: application/json' "${AUTH[@]}" \
  -d '{"actor":"agent:smoke","action":"http.request","target":"https://api.anthropic.com/v1/messages"}'; echo
curl -fsS -X POST "$BASE/v1/policy/evaluate" -H 'content-type: application/json' "${AUTH[@]}" \
  -d '{"actor":"agent:smoke","action":"http.request","target":"https://blocked.example.com"}'; echo
