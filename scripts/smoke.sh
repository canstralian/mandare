#!/usr/bin/env bash
# Smoke test against a running `rif serve`.
#
#   RIF_API_KEY=<key> BASE=http://127.0.0.1:8000 ./scripts/smoke.sh
#
# The key must be one of the comma-separated values the server was started with
# in RIF_CONTROL_PLANE_API_KEYS. Control-plane routes fail closed: without a
# configured key the server answers 503, with a wrong key 401.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8000}"
API_KEY="${RIF_API_KEY:-}"

if [[ -z "$API_KEY" ]]; then
  echo "RIF_API_KEY is not set; /v1/policy/evaluate is auth-guarded and would fail." >&2
  echo "Start the server with RIF_CONTROL_PLANE_API_KEYS=<key> and re-run with RIF_API_KEY=<key>." >&2
  exit 2
fi

# Unauthenticated read-only routes.
curl -fsS "$BASE/health"; echo
curl -fsS "$BASE/v1/environments"; echo
curl -fsS "$BASE/v1/audit"; echo
curl -fsS "$BASE/v1/recovered-state"; echo

# Guarded evaluation: allowed host, then denied host.
curl -fsS -X POST "$BASE/v1/policy/evaluate" \
  -H 'content-type: application/json' \
  -H "X-API-Key: $API_KEY" \
  -d '{"actor":"agent:smoke","action":"http.request","target":"https://api.anthropic.com/v1/messages"}'; echo
curl -fsS -X POST "$BASE/v1/policy/evaluate" \
  -H 'content-type: application/json' \
  -H "X-API-Key: $API_KEY" \
  -d '{"actor":"agent:smoke","action":"http.request","target":"https://blocked.example.com"}'; echo
