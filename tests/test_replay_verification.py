"""Replay verification and JSON-native decision ledger round-trips."""

import json
from datetime import UTC, datetime

from rif_runtime.replay import ReplayEngine
from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import Decision, PolicyDecision, PolicyRequest, Posture


def _seed_log(tmp_path, rows: list[dict]) -> str:
    log = tmp_path / "decisions.jsonl"
    log.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n",
        encoding="utf-8",
    )
    return str(log)


def test_verify_reports_valid_and_deterministic(tmp_path):
    stamped = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    rows = [
        PolicyDecision(
            decision=Decision.allow,
            actor="agent:a",
            action="http.request",
            target="https://api.anthropic.com",
            environment="RIF_CI",
            posture=Posture.normal,
            reason="ok",
            matched_rule="default.allow",
            timestamp=stamped,
        ).model_dump(mode="json"),
        PolicyDecision(
            decision=Decision.deny,
            actor="agent:a",
            action="http.request",
            target="https://evil.example.com",
            environment="RIF_CI",
            posture=Posture.normal,
            reason="denied",
            matched_rule="network.host.denied",
            timestamp=stamped,
        ).model_dump(mode="json"),
    ]
    engine = ReplayEngine(_seed_log(tmp_path, rows))
    report = engine.verify()
    assert report.row_count == 2
    assert report.valid_decisions == 2
    assert report.invalid_rows == 0
    assert report.errors == []
    assert report.deterministic is True
    assert report.recovered is not None
    assert report.recovered.historical_denials == 1
    assert report.recovered.last_posture == "normal"


def test_verify_reports_corrupt_rows_without_silent_skip(tmp_path):
    log = tmp_path / "decisions.jsonl"
    log.write_text(
        '{"decision":"allow","actor":"a","action":"http.request",'
        '"target":"https://x","environment":"e","posture":"normal",'
        '"reason":"r","matched_rule":"default.allow",'
        '"timestamp":"2026-01-02T03:04:05Z"}\n'
        "not-json\n"
        '{"decision":"deny"}\n',
        encoding="utf-8",
    )
    report = ReplayEngine(str(log)).verify()
    assert report.row_count == 3
    assert report.valid_decisions == 1
    assert report.invalid_rows == 2
    assert len(report.errors) == 2
    assert report.deterministic is False
    assert report.recovered is None


def test_recover_twice_is_bit_identical_for_valid_log(tmp_path):
    rows = [
        {
            "decision": "deny",
            "actor": "agent:a",
            "action": "http.request",
            "target": "https://evil.example.com",
            "environment": "RIF_CI",
            "posture": "normal",
            "reason": "denied",
            "matched_rule": "network.host.denied",
            "timestamp": "2026-01-02T03:04:05Z",
        }
        for _ in range(3)
    ]
    engine = ReplayEngine(_seed_log(tmp_path, rows))
    assert engine.recover() == engine.recover()
    assert engine.recover().last_posture == "elevated"


def test_runtime_persists_json_native_timestamps(tmp_path, monkeypatch):
    # Decisions written by RIFRuntime must be JSON-native ISO timestamps so
    # forensic tools do not depend on default=str coercion.
    from rif_runtime.evidence import EvidenceLedger
    from rif_runtime.storage.jsonl import JsonlStore

    decisions = tmp_path / "decisions.jsonl"
    runtime = RIFRuntime()
    runtime.evidence_ledger = EvidenceLedger(decisions)
    runtime.decisions_store = runtime.evidence_ledger.store
    runtime.posture_store = JsonlStore(tmp_path / "posture_history.jsonl")
    runtime.evidence_store = JsonlStore(tmp_path / "metasploit_evidence.jsonl")

    runtime.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="https://blocked.example.com",
        )
    )
    line = decisions.read_text(encoding="utf-8").strip().splitlines()[-1]
    row = json.loads(line)
    assert "T" in row["timestamp"]  # ISO-8601 from mode="json"
    assert row["schema_version"] == "rif.evidence.decision/v1"
    # Round-trip through replay validation
    assert ReplayEngine(str(decisions)).verify().invalid_rows == 0
    assert ReplayEngine(str(decisions)).verify().chain_ok is True
