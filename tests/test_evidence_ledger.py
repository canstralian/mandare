"""Evidence ledger: additive v1 envelope, legacy readability, stable export."""

import json
from datetime import UTC, datetime

from rif_runtime.evidence import (
    DECISION_SCHEMA_V1,
    EvidenceLedger,
    content_hash,
    enrich_decision_row,
)
from rif_runtime.replay import ReplayEngine
from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import Decision, PolicyDecision, PolicyRequest, Posture
from rif_runtime.storage.jsonl import JsonlStore


def _decision(
    *,
    target: str = "https://evil.example.com",
    decision: Decision = Decision.deny,
    timestamp: datetime | None = None,
) -> PolicyDecision:
    return PolicyDecision(
        decision=decision,
        actor="agent:test",
        action="http.request",
        target=target,
        environment="RIF_CI",
        posture=Posture.normal,
        reason="test",
        matched_rule="network.host.denied"
        if decision == Decision.deny
        else "default.allow",
        timestamp=timestamp or datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    )


def test_enrich_decision_row_adds_v1_envelope():
    row = enrich_decision_row(_decision(), sequence=1, previous_hash=None)
    assert row["schema_version"] == DECISION_SCHEMA_V1
    assert row["sequence"] == 1
    assert row["previous_hash"] is None
    assert row["record_hash"] == content_hash(row)
    # Core PolicyDecision fields remain present for legacy readers.
    assert row["decision"] == "deny"
    assert row["actor"] == "agent:test"


def test_legacy_rows_remain_readable_and_replayable(tmp_path):
    legacy = {
        "decision": "allow",
        "actor": "agent:a",
        "action": "http.request",
        "target": "https://api.anthropic.com",
        "environment": "RIF_CI",
        "posture": "normal",
        "reason": "seeded",
        "matched_rule": "default.allow",
        "timestamp": "2026-01-02T03:04:05Z",
    }
    log = tmp_path / "decisions.jsonl"
    log.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    decision = ReplayEngine(str(log))._decision_from_row(legacy)
    assert decision.decision == Decision.allow

    report = ReplayEngine(str(log)).verify()
    assert report.invalid_rows == 0
    assert report.deterministic is True
    assert report.chain_ok is True
    assert report.legacy_rows == 1
    assert report.v1_rows == 0


def test_ledger_appends_causal_chain(tmp_path):
    ledger = EvidenceLedger(tmp_path / "decisions.jsonl")
    first = ledger.append_decision(_decision(target="https://a.example.com"))
    second = ledger.append_decision(_decision(target="https://b.example.com"))

    assert first["sequence"] == 1
    assert first["previous_hash"] is None
    assert second["sequence"] == 2
    assert second["previous_hash"] == first["record_hash"]

    chain = ledger.verify_chain()
    assert chain.chain_ok is True
    assert chain.v1_rows == 2
    assert chain.legacy_rows == 0


def test_v1_links_across_legacy_prefix_without_rewrite(tmp_path):
    log = tmp_path / "decisions.jsonl"
    legacy = _decision(target="https://legacy.example.com").model_dump(mode="json")
    # Deliberately omit envelope fields — pre-v1 shape.
    log.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    ledger = EvidenceLedger(log)
    assert ledger.sequence == 1
    row = ledger.append_decision(_decision(target="https://new.example.com"))
    assert row["sequence"] == 2
    assert row["previous_hash"] == content_hash(legacy)

    chain = ledger.verify_chain()
    assert chain.chain_ok is True
    assert chain.legacy_rows == 1
    assert chain.v1_rows == 1

    # Replay still rebuilds from mixed log.
    recovered = ReplayEngine(str(log)).recover()
    assert recovered.historical_decisions == 2


def test_tampered_record_hash_fails_chain(tmp_path):
    ledger = EvidenceLedger(tmp_path / "decisions.jsonl")
    ledger.append_decision(_decision())
    rows = ledger.read_all()
    rows[0]["reason"] = "tampered"
    log = tmp_path / "decisions.jsonl"
    log.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")

    report = EvidenceLedger(log).verify_chain()
    assert report.chain_ok is False
    assert any("record_hash mismatch" in e for e in report.errors)


def test_export_stable_json_is_byte_stable(tmp_path):
    ledger = EvidenceLedger(tmp_path / "decisions.jsonl")
    ledger.append_decision(_decision(target="https://a.example.com"))
    ledger.append_decision(_decision(target="https://b.example.com"))

    first = ledger.export_stable_json()
    second = ledger.export_stable_json()
    assert first == second
    payload = json.loads(first)
    assert isinstance(payload, list)
    assert payload[0]["schema_version"] == DECISION_SCHEMA_V1
    # sort_keys: schema_version appears after record_hash alphabetically...
    # just assert keys are sorted in the serialized object text for first record.
    assert '"record_hash"' in first
    assert first.index('"actor"') < first.index('"decision"')


def test_runtime_writes_v1_envelope(tmp_path):
    runtime = RIFRuntime()
    log = tmp_path / "decisions.jsonl"
    runtime.evidence_ledger = EvidenceLedger(log)
    runtime.decisions_store = runtime.evidence_ledger.store
    runtime.posture_store = JsonlStore(tmp_path / "posture.jsonl")
    runtime.evidence_store = JsonlStore(tmp_path / "msf.jsonl")

    runtime.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="https://blocked.example.com",
        )
    )
    row = json.loads(log.read_text(encoding="utf-8").strip())
    assert row["schema_version"] == DECISION_SCHEMA_V1
    assert row["sequence"] == 1
    assert "T" in row["timestamp"]
    assert ReplayEngine(str(log)).verify().chain_ok is True


def test_example_evidence_record_shape():
    """Normative example of a v1 decision evidence record."""

    stamped = datetime(2026, 8, 7, 14, 0, 0, tzinfo=UTC)
    row = enrich_decision_row(
        _decision(timestamp=stamped),
        sequence=1,
        previous_hash=None,
    )
    expected_keys = {
        "decision",
        "actor",
        "action",
        "target",
        "environment",
        "posture",
        "reason",
        "matched_rule",
        "timestamp",
        "schema_version",
        "sequence",
        "previous_hash",
        "record_hash",
    }
    assert set(row) == expected_keys
    assert row["schema_version"] == "rif.evidence.decision/v1"
    assert row["timestamp"] == "2026-08-07T14:00:00Z"
    assert len(row["record_hash"]) == 64
