"""Composition-root ownership: transports delegate; Runtime owns replay."""

from __future__ import annotations

import json

from rif_runtime.replay import ReplayEngine
from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import Posture


def _decision_row(actor: str, target: str, decision: str = "allow") -> dict:
    return {
        "decision": decision,
        "actor": actor,
        "action": "http.request",
        "target": target,
        "environment": "RIF_CI",
        "posture": "normal",
        "reason": "seeded",
        "matched_rule": "default.allow",
    }


def test_runtime_owns_replay_engine_by_default() -> None:
    r = RIFRuntime()
    assert isinstance(r.replay, ReplayEngine)
    assert str(r.replay.decisions_path) == str(r.decisions_store.path)


def test_recovered_state_uses_injected_replay(tmp_path) -> None:
    log = tmp_path / "decisions.jsonl"
    rows = [
        _decision_row("agent:a", "https://x.example.com"),
        _decision_row("agent:a", "https://y.example.com", decision="deny"),
        _decision_row("agent:b", "https://y.example.com", decision="deny"),
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    r = RIFRuntime(replay=ReplayEngine(str(log)))
    body = r.recovered_state()
    assert body["historical_decisions"] == 3
    assert body["historical_denials"] == 2
    assert body["graph_nodes"] == 4
    assert body["graph_edges"] == 3
    assert body["last_posture"] == "normal"


def test_set_and_reset_posture() -> None:
    r = RIFRuntime()
    assert r.set_posture(Posture.elevated) == Posture.elevated
    assert r.posture == Posture.elevated
    assert r.reset_posture() == Posture.normal
    assert r.posture == Posture.normal


def test_audit_delegates_through_runtime() -> None:
    r = RIFRuntime()
    summary = r.audit()
    assert "agent" in summary or "environment" in summary or "live" in summary
