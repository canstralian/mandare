"""Restart semantics: persisted state must survive process reconstruction."""

import json

from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import Posture


def test_locked_runtime_stays_locked_after_restart(tmp_path):
    # A locked posture denies everything, so losing it on restart silently
    # re-opens the runtime.
    first = RIFRuntime(data_dir=tmp_path)
    first.set_posture(Posture.locked)

    restarted = RIFRuntime(data_dir=tmp_path)
    assert restarted.posture == Posture.locked


def test_restart_restores_posture_from_decisions_when_no_history(tmp_path):
    # No posture_history.jsonl (e.g. a log written before transitions were
    # recorded): the decision log's denial count is the fallback source.
    log = tmp_path / "decisions.jsonl"
    row = {
        "decision": "deny",
        "actor": "agent:test",
        "action": "http.request",
        "target": "https://blocked.example.com",
        "environment": "RIF_CI",
        "posture": "normal",
        "reason": "seeded",
        "matched_rule": "network.host.denied",
    }
    log.write_text(
        "\n".join(json.dumps(row) for _ in range(20)) + "\n", encoding="utf-8"
    )

    assert RIFRuntime(data_dir=tmp_path).posture == Posture.locked


def test_restart_honours_a_reset(tmp_path):
    # An operator reset is a recorded transition, so it must win over the
    # earlier escalation rather than being replayed away.
    first = RIFRuntime(data_dir=tmp_path)
    first.set_posture(Posture.locked)
    first.set_posture(Posture.normal)

    assert RIFRuntime(data_dir=tmp_path).posture == Posture.normal


def test_data_dir_owns_every_store(tmp_path):
    runtime = RIFRuntime(data_dir=tmp_path)

    assert runtime.decisions_path == tmp_path / "decisions.jsonl"
    assert runtime.posture_store.path == tmp_path / "posture_history.jsonl"
    assert runtime.evidence_store.path == tmp_path / "metasploit_evidence.jsonl"
    assert runtime.policy_store.store.path == tmp_path / "policies.json"
