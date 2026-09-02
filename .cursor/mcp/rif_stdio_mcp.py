#!/usr/bin/env python3
"""Local stdio MCP adapters for Cursor.

These servers are Cursor agent infrastructure, not the RIF MCP governance
framework in ``src/rif_runtime/mcp/``. They wrap existing Python APIs:

- rif-policy: ``RIFRuntime.evaluate(..., record=False)`` (no persistence)
- rif-replay: ``ReplayEngine.recover()``
- rif-evidence: persisted summaries, recent redacted rows, hash-chain verify

Stdout is reserved for MCP JSON-RPC. Logs go to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "0.1.0"
SURFACES = ("policy", "replay", "evidence")

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("ascii", errors="replace")
        key, sep, value = decoded.partition(":")
        if not sep:
            continue
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    if not body:
        return None
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("MCP message must be a JSON object")
    return payload


def _write_message(message: dict[str, Any]) -> None:
    body = json.dumps(message, default=str).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _text_result(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    if isinstance(payload, str):
        text = payload
    else:
        text = json.dumps(payload, indent=2, default=str)
    return {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }


def _json_schema(
    properties: dict[str, Any], required: list[str] | None = None
) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _policy_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "policy_check",
            "description": (
                "Evaluate a RIF policy request without persisting a decision. "
                "Uses RIFRuntime.evaluate(record=False). Does not call /v1/mcp/invoke."
            ),
            "inputSchema": _json_schema(
                {
                    "actor": {"type": "string"},
                    "action": {"type": "string"},
                    "target": {"type": "string"},
                },
                ["actor", "action", "target"],
            ),
        }
    ]


def _replay_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "replay_recover",
            "description": (
                "Rebuild graph/posture summary from a decisions JSONL log. "
                "Read-only. Defaults to the configured data directory."
            ),
            "inputSchema": _json_schema(
                {
                    "decisions_path": {
                        "type": "string",
                        "description": "Optional path to decisions.jsonl",
                    }
                }
            ),
        }
    ]


def _evidence_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "evidence_summary",
            "description": (
                "Read persisted decision/posture/audit summaries from local JSONL."
            ),
            "inputSchema": _json_schema({}),
        },
        {
            "name": "evidence_recent",
            "description": (
                "Return the most recent persisted decision rows with secrets redacted."
            ),
            "inputSchema": _json_schema(
                {
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Number of trailing rows (default 20)",
                    }
                }
            ),
        },
        {
            "name": "evidence_verify_chain",
            "description": "Recompute the persisted decision-log hash chain.",
            "inputSchema": _json_schema({}),
        },
    ]


def _handle_policy_check(arguments: dict[str, Any]) -> dict[str, Any]:
    from rif_runtime.runtime import RIFRuntime
    from rif_runtime.schemas import PolicyRequest

    actor = str(arguments.get("actor", "")).strip()
    action = str(arguments.get("action", "")).strip()
    target = str(arguments.get("target", "")).strip()
    if not actor or not action or not target:
        return _text_result("actor, action, and target are required", is_error=True)
    runtime = RIFRuntime()
    decision = runtime.evaluate(
        PolicyRequest(actor=actor, action=action, target=target),
        record=False,
    )
    return _text_result(
        {
            "recorded": False,
            "decision": decision.model_dump(mode="json"),
        }
    )


def _handle_replay_recover(arguments: dict[str, Any]) -> dict[str, Any]:
    from rif_runtime.replay import ReplayEngine

    path = arguments.get("decisions_path")
    engine = ReplayEngine(path if path else None)
    state = engine.recover()
    return _text_result(
        {
            "decisions_path": str(engine.decisions_path),
            "historical_decisions": state.historical_decisions,
            "historical_denials": state.historical_denials,
            "graph_nodes": state.graph_nodes,
            "graph_edges": state.graph_edges,
            "last_posture": state.last_posture,
        }
    )


def _handle_evidence_summary(_arguments: dict[str, Any]) -> dict[str, Any]:
    from rif_runtime.runtime import RIFRuntime
    from rif_runtime.security import redact_secrets

    runtime = RIFRuntime()
    return _text_result(
        redact_secrets(
            {
                "data_dir": str(runtime.data_dir),
                "persisted": runtime.persisted_summary(),
                "audit": runtime.audit_summary(),
            }
        )
    )


def _handle_evidence_recent(arguments: dict[str, Any]) -> dict[str, Any]:
    from rif_runtime.runtime import RIFRuntime
    from rif_runtime.security import redact_secrets

    limit = arguments.get("limit", 20)
    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        return _text_result("limit must be an integer", is_error=True)
    parsed = max(1, min(parsed, 100))
    runtime = RIFRuntime()
    rows = runtime.decisions_store.read_all()
    return _text_result(
        redact_secrets(
            {
                "data_dir": str(runtime.data_dir),
                "returned": min(parsed, len(rows)),
                "total": len(rows),
                "rows": rows[-parsed:],
            }
        )
    )


def _handle_evidence_verify_chain(_arguments: dict[str, Any]) -> dict[str, Any]:
    from rif_runtime.runtime import RIFRuntime
    from rif_runtime.security import redact_secrets

    runtime = RIFRuntime()
    return _text_result(redact_secrets(runtime.verify_decision_chain()))


def _tools_for(surface: str) -> tuple[list[dict[str, Any]], dict[str, ToolHandler]]:
    if surface == "policy":
        return _policy_tools(), {"policy_check": _handle_policy_check}
    if surface == "replay":
        return _replay_tools(), {"replay_recover": _handle_replay_recover}
    if surface == "evidence":
        return _evidence_tools(), {
            "evidence_summary": _handle_evidence_summary,
            "evidence_recent": _handle_evidence_recent,
            "evidence_verify_chain": _handle_evidence_verify_chain,
        }
    raise ValueError(f"unknown surface: {surface}")


def _initialize_result(surface: str) -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": f"rif-{surface}", "version": SERVER_VERSION},
    }


def _dispatch(surface: str, message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    msg_id = message.get("id")
    if not isinstance(method, str):
        if msg_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32600, "message": "Invalid Request"},
            }
        return None
    if method == "notifications/initialized" or method.startswith("notifications/"):
        return None
    if msg_id is None:
        return None
    tools, handlers = _tools_for(surface)
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": _initialize_result(surface)}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = handlers.get(str(name))
        if handler is None:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": _text_result(f"unknown tool: {name}", is_error=True),
            }
        if not isinstance(arguments, dict):
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": _text_result("arguments must be an object", is_error=True),
            }
        try:
            result = handler(arguments)
        except Exception as exc:
            _log(f"tool {name} failed: {exc}")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": _text_result(str(exc), is_error=True),
            }
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def serve(surface: str) -> None:
    _log(f"rif stdio MCP surface={surface}")
    while True:
        try:
            message = _read_message()
        except json.JSONDecodeError as exc:
            _log(f"invalid JSON: {exc}")
            continue
        if message is None:
            return
        response = _dispatch(surface, message)
        if response is not None:
            _write_message(response)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RIF Cursor stdio MCP adapter")
    parser.add_argument(
        "--surface",
        required=True,
        choices=SURFACES,
        help="MCP surface: policy, replay, or evidence",
    )
    args = parser.parse_args(argv)
    serve(args.surface)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
