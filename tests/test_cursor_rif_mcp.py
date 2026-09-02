"""Cursor stdio MCP adapters wrap existing RIF APIs without new authority."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import PolicyRequest

SERVER = Path(__file__).resolve().parents[1] / ".cursor" / "mcp" / "rif_stdio_mcp.py"
MCP_JSON = Path(__file__).resolve().parents[1] / ".cursor" / "mcp.json"


def _encode(message: dict) -> bytes:
    body = json.dumps(message).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def _read(proc: subprocess.Popen[bytes]) -> dict:
    headers: dict[str, str] = {}
    assert proc.stdout is not None
    while True:
        line = proc.stdout.readline()
        assert line, "MCP server closed stdout before completing the response"
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("ascii").partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers["content-length"])
    body = proc.stdout.read(length)
    return json.loads(body.decode("utf-8"))


def _rpc(
    surface: str,
    messages: list[dict],
    *,
    data_dir: Path,
) -> list[dict]:
    env = {
        **os.environ,
        "RIF_DATA_DIR": str(data_dir),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "PYTHONUNBUFFERED": "1",
    }
    proc = subprocess.Popen(
        [sys.executable, "-u", str(SERVER), "--surface", surface],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert proc.stdin is not None
    try:
        for message in messages:
            proc.stdin.write(_encode(message))
        proc.stdin.close()
        responses = [_read(proc) for _ in messages if "id" in _]
        proc.wait(timeout=15)
        return responses
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_mcp_json_registers_allowlisted_stdio_servers_only() -> None:
    payload = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    servers = payload["mcpServers"]
    assert set(servers) == {"rif-policy", "rif-replay", "rif-evidence"}
    for name, spec in servers.items():
        surface = name.removeprefix("rif-")
        assert spec["command"] == "python3"
        assert spec["args"] == [
            "-u",
            ".cursor/mcp/rif_stdio_mcp.py",
            "--surface",
            surface,
        ]
        assert spec["env"] == {"PYTHONPATH": "src"}
        assert "env" in spec
        joined = json.dumps(spec)
        assert "sk-" not in joined
        assert "ghp_" not in joined


def test_policy_surface_initialize_and_lists_check_tool(tmp_path: Path) -> None:
    responses = _rpc(
        "policy",
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ],
        data_dir=tmp_path,
    )
    assert responses[0]["result"]["serverInfo"]["name"] == "rif-policy"
    names = {tool["name"] for tool in responses[1]["result"]["tools"]}
    assert names == {"policy_check"}


def test_policy_check_does_not_persist_decisions(tmp_path: Path) -> None:
    responses = _rpc(
        "policy",
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "policy_check",
                    "arguments": {
                        "actor": "agent:test",
                        "action": "http.request",
                        "target": "https://evil.example",
                    },
                },
            }
        ],
        data_dir=tmp_path,
    )
    result = responses[0]["result"]
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["recorded"] is False
    assert payload["decision"]["decision"] in {"allow", "deny", "review"}
    assert not (tmp_path / "decisions.jsonl").exists()


def test_replay_and_evidence_read_persisted_state(tmp_path: Path) -> None:
    runtime = RIFRuntime(tmp_path)
    runtime.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="https://evil.example",
        )
    )
    replay = _rpc(
        "replay",
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "replay_recover", "arguments": {}},
            }
        ],
        data_dir=tmp_path,
    )
    recovered = json.loads(replay[0]["result"]["content"][0]["text"])
    assert recovered["historical_decisions"] >= 1
    evidence = _rpc(
        "evidence",
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "evidence_summary", "arguments": {}},
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "evidence_recent", "arguments": {"limit": 5}},
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "evidence_verify_chain", "arguments": {}},
            },
        ],
        data_dir=tmp_path,
    )
    summary = json.loads(evidence[0]["result"]["content"][0]["text"])
    assert summary["persisted"]["decisions_total"] >= 1
    recent = json.loads(evidence[1]["result"]["content"][0]["text"])
    assert recent["total"] >= 1
    chain = json.loads(evidence[2]["result"]["content"][0]["text"])
    assert chain["verified"] is True


def test_unknown_surface_is_rejected() -> None:
    result = subprocess.run(
        [sys.executable, str(SERVER), "--surface", "firecrawl"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "invalid choice" in result.stderr.lower() or "error" in result.stderr.lower()
