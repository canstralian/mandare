"""Replay must preserve persisted decision timestamps."""

import json
from datetime import UTC, datetime

from rif_runtime.replay import ReplayEngine
from rif_runtime.schemas import Decision, PolicyDecision, Posture


def test_decision_from_row_preserves_timestamp(tmp_path):
    # Regression: manual field picking dropped timestamp, so replay minted a
    # fresh now() and poisoned forensic graph edge times.
    stamped = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    row = PolicyDecision(
        decision=Decision.deny,
        actor="agent:a",
        action="http.request",
        target="https://evil.example.com",
        environment="RIF_CI",
        posture=Posture.normal,
        reason="host denied",
        matched_rule="network.host.denied",
        timestamp=stamped,
    ).model_dump(mode="json")

    log = tmp_path / "decisions.jsonl"
    log.write_text(json.dumps(row) + "\n", encoding="utf-8")

    engine = ReplayEngine(str(log))
    decision = engine._decision_from_row(engine._rows()[0])
    assert decision.timestamp == stamped


def test_decision_from_row_accepts_legacy_space_separated_timestamp():
    engine = ReplayEngine()
    row = {
        "decision": "allow",
        "actor": "agent:a",
        "action": "http.request",
        "target": "https://api.anthropic.com",
        "environment": "RIF_CI",
        "posture": "normal",
        "reason": "seeded",
        "matched_rule": "default.allow",
        # Legacy form from json.dumps(..., default=str) on a datetime
        "timestamp": "2026-01-02 03:04:05+00:00",
    }
    decision = engine._decision_from_row(row)
    assert decision.timestamp == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
