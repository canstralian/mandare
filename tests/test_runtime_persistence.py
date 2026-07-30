"""Persistence-path regressions: recovered state, audit record format, tallies."""

from rif_runtime.replay import ReplayEngine
from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import PolicyRequest, Posture
from rif_runtime.storage.jsonl import JsonlStore


def _isolated_runtime(tmp_path) -> RIFRuntime:
    """A runtime whose stores point at tmp_path instead of the shared data/."""
    runtime = RIFRuntime()
    runtime.decisions_store = JsonlStore(tmp_path / "decisions.jsonl")
    runtime.posture_store = JsonlStore(tmp_path / "posture_history.jsonl")
    runtime.evidence_store = JsonlStore(tmp_path / "evidence.jsonl")
    return runtime


def _deny(runtime: RIFRuntime, n: int) -> None:
    for i in range(n):
        runtime.evaluate(
            PolicyRequest(
                actor="agent:test",
                action="http.request",
                target=f"https://blocked{i}.example.com",
            )
        )


def test_posture_transitions_record_plain_enum_values(tmp_path):
    # Regression: transitions were written with str(Posture.normal), which a
    # `str, Enum` renders as "Posture.normal" -- not the plain "normal" that
    # pydantic writes into decisions.jsonl for the same field.
    runtime = _isolated_runtime(tmp_path)
    _deny(runtime, 3)

    rows = runtime.posture_store.read_all()
    assert rows, "expected a posture transition after three denials"
    assert rows[0] == {"old_posture": "normal", "new_posture": "elevated"}

    decisions = runtime.decisions_store.read_all()
    assert {row["posture"] for row in decisions} <= {p.value for p in Posture}


def test_recovered_summary_replays_the_decision_log(tmp_path):
    runtime = _isolated_runtime(tmp_path)
    _deny(runtime, 3)

    recovered = runtime.recovered_summary()
    assert recovered["historical_decisions"] == 3
    assert recovered["historical_denials"] == 3
    assert recovered["graph_edges"] == 3
    assert recovered["last_posture"] == "elevated"


def test_recovered_summary_on_an_empty_log(tmp_path):
    runtime = _isolated_runtime(tmp_path)
    assert runtime.recovered_summary() == {
        "historical_decisions": 0,
        "historical_denials": 0,
        "graph_nodes": 0,
        "graph_edges": 0,
        "last_posture": "normal",
    }


def test_replay_engine_and_live_runtime_agree_on_posture(tmp_path):
    # Replay derives posture from the same ladder the live loop uses, so a
    # cold start must land on the rung the live runtime reached.
    runtime = _isolated_runtime(tmp_path)
    _deny(runtime, 10)

    replayed = ReplayEngine(str(runtime.decisions_store.path)).recover()
    assert replayed.last_posture == runtime.posture.value == "restricted"


def test_persisted_summary_tallies_match_the_log(tmp_path):
    runtime = _isolated_runtime(tmp_path)
    _deny(runtime, 2)
    runtime.evaluate(
        PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="https://api.anthropic.com/v1/messages",
        )
    )

    summary = runtime.persisted_summary()
    assert summary["decisions_total"] == 3
    assert summary["decisions_by_result"] == {"deny": 2, "allow": 1}
    assert sum(summary["decisions_by_rule"].values()) == 3


def test_jsonl_summarise_tallies_every_field_in_one_pass(tmp_path):
    store = JsonlStore(tmp_path / "log.jsonl")
    store.append({"decision": "allow", "matched_rule": "default.allow"})
    store.append({"decision": "deny", "matched_rule": "network.host.denied"})
    store.append({"decision": "deny", "matched_rule": "network.host.denied"})

    tallies = store.summarise("decision", "matched_rule")
    assert tallies == {
        "decision": {"allow": 1, "deny": 2},
        "matched_rule": {"default.allow": 1, "network.host.denied": 2},
    }
    # count_by is kept as a thin wrapper over the same pass.
    assert store.count_by("decision") == {"allow": 1, "deny": 2}
    assert store.count() == 3


def test_jsonl_summarise_marks_missing_fields_unknown(tmp_path):
    store = JsonlStore(tmp_path / "log.jsonl")
    store.append({"decision": "allow"})
    assert store.summarise("matched_rule") == {"matched_rule": {"unknown": 1}}
