#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8000}"
curl -fsS "$BASE/health"; echo
curl -fsS "$BASE/v1/environments"; echo
curl -fsS "$BASE/v1/audit"; echo
curl -fsS -X POST "$BASE/v1/policy/evaluate" -H 'content-type: application/json' -d '{"actor":"agent:smoke","action":"http.request","target":"https://api.anthropic.com/v1/messages"}'; echo
curl -fsS -X POST "$BASE/v1/policy/evaluate" -H 'content-type: application/json' -d '{"actor":"agent:smoke","action":"http.request","target":"https://blocked.example.com"}'; echo
