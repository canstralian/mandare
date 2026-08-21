import json
from dataclasses import replace

from rif_runtime.audit import GENESIS_HASH, append_record, verify_chain
from rif_runtime.configuration.policies import PolicyRule
from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import PolicyRequest
from rif_runtime.storage.jsonl import CHAIN_KEY, HashChainedJsonlStore, JsonlStore


def test_empty_chain_is_valid():
    assert verify_chain([])


def test_append_record_links_to_genesis_hash():
    record = append_record(
        [],
        {"decision": "ALLOW"},
        event_id="evt-1",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert record.previous_hash == GENESIS_HASH
    assert len(record.current_hash) == 64


def test_multiple_records_form_valid_chain():
    chain = []
    first = append_record(
        chain,
        {"decision": "ALLOW"},
        event_id="evt-1",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    chain.append(first)

    second = append_record(
        chain,
        {"decision": "DENY"},
        event_id="evt-2",
        timestamp="2026-01-01T00:01:00+00:00",
    )
    chain.append(second)

    assert second.previous_hash == first.current_hash
    assert verify_chain(chain)


def test_payload_tampering_breaks_chain():
    chain = []
    first = append_record(
        chain,
        {"decision": "ALLOW"},
        event_id="evt-1",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    chain.append(first)

    second = append_record(
        chain,
        {"decision": "DENY"},
        event_id="evt-2",
        timestamp="2026-01-01T00:01:00+00:00",
    )
    chain.append(second)

    tampered = replace(first, payload={"decision": "DENY"})
    assert not verify_chain([tampered, second])


def test_previous_hash_tampering_breaks_chain():
    chain = []
    first = append_record(
        chain,
        {"decision": "ALLOW"},
        event_id="evt-1",
        timestamp="2026-01-01T00:00:00+00:00",
    )
    chain.append(first)

    second = append_record(
        chain,
        {"decision": "DENY"},
        event_id="evt-2",
        timestamp="2026-01-01T00:01:00+00:00",
    )
    chain.append(second)

    tampered = replace(second, previous_hash="x" * 64)
    assert not verify_chain([first, tampered])


# --- hash-chained decision log -----------------------------------------------
#
# audit.py implemented this chain from the start, but nothing in src/ used it:
# decisions.jsonl was append-only, not tamper-evident. These cover the wiring.


def _decision(target: str = "https://api.anthropic.com") -> PolicyRequest:
    return PolicyRequest(actor="agent:test", action="http.request", target=target)


def _allowing_runtime(tmp_path) -> RIFRuntime:
    runtime = RIFRuntime(data_dir=tmp_path)
    runtime.policy_store.upsert(
        PolicyRule(
            id="allow_test_traffic",
            effect="allow",
            action="http.request",
            target="*",
            reason="chain tests",
        )
    )
    return runtime


def test_appended_rows_carry_a_chain_envelope(tmp_path):
    store = HashChainedJsonlStore(tmp_path / "log.jsonl")
    store.append({"event": "first"})
    store.append({"event": "second"})

    rows = store.read_all()
    assert [row["event"] for row in rows] == ["first", "second"]
    assert rows[0][CHAIN_KEY]["previous_hash"] == GENESIS_HASH
    assert rows[1][CHAIN_KEY]["previous_hash"] == rows[0][CHAIN_KEY]["current_hash"]


def test_untouched_chain_verifies(tmp_path):
    store = HashChainedJsonlStore(tmp_path / "log.jsonl")
    for index in range(5):
        store.append({"event": index})

    result = store.verify()
    assert result.verified is True
    assert result.chained_rows == 5
    assert result.unchained_leading == 0
    assert result.broken_at is None


def test_editing_a_payload_breaks_verification(tmp_path):
    """The whole point: a silently edited row must be detectable."""
    path = tmp_path / "log.jsonl"
    store = HashChainedJsonlStore(path)
    for index in range(4):
        store.append({"event": index, "decision": "deny"})

    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[1]["decision"] = "allow"  # flip a denial to an allow, leave hashes alone
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    result = HashChainedJsonlStore(path).verify()
    assert result.verified is False
    assert result.broken_at == 1


def test_deleting_a_row_breaks_verification(tmp_path):
    path = tmp_path / "log.jsonl"
    store = HashChainedJsonlStore(path)
    for index in range(4):
        store.append({"event": index})

    rows = [json.loads(line) for line in path.read_text().splitlines()]
    del rows[1]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    result = HashChainedJsonlStore(path).verify()
    assert result.verified is False
    assert result.broken_at == 1


def test_reordering_rows_breaks_verification(tmp_path):
    path = tmp_path / "log.jsonl"
    store = HashChainedJsonlStore(path)
    for index in range(4):
        store.append({"event": index})

    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[1], rows[2] = rows[2], rows[1]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    assert HashChainedJsonlStore(path).verify().verified is False


def test_legacy_unchained_rows_are_reported_not_silently_verified(tmp_path):
    """An existing decisions.jsonl predates chaining; it must still load."""
    path = tmp_path / "log.jsonl"
    legacy = JsonlStore(path)
    legacy.append({"event": "old-1"})
    legacy.append({"event": "old-2"})

    store = HashChainedJsonlStore(path)
    store.append({"event": "new-1"})

    result = store.verify()
    assert result.verified is True
    assert result.unchained_leading == 2
    assert result.chained_rows == 1
    assert len(store.read_all()) == 3


def test_unchained_row_appended_after_chaining_is_a_break(tmp_path):
    path = tmp_path / "log.jsonl"
    store = HashChainedJsonlStore(path)
    store.append({"event": "chained"})
    JsonlStore(path).append({"event": "spliced-in-by-hand"})

    result = HashChainedJsonlStore(path).verify()
    assert result.verified is False
    assert result.broken_at == 1


def test_chain_survives_reopening_the_store(tmp_path):
    """The cached tail hash must be recovered from disk, not restarted."""
    path = tmp_path / "log.jsonl"
    HashChainedJsonlStore(path).append({"event": "before-restart"})
    HashChainedJsonlStore(path).append({"event": "after-restart"})

    result = HashChainedJsonlStore(path).verify()
    assert result.verified is True
    assert result.chained_rows == 2


def test_recorded_decisions_produce_a_verifiable_chain(tmp_path):
    """End to end: real decisions, hashed payloads, verified after the fact.

    Guards the serialisation trap specifically -- PolicyDecision carries a
    datetime, and hashing an isoformat string while persisting a str()-formatted
    one would make verification impossible.
    """
    runtime = _allowing_runtime(tmp_path)
    runtime.evaluate(_decision())
    runtime.evaluate(_decision("https://blocked.example.net"))

    result = runtime.verify_decision_chain()
    assert result["verified"] is True
    assert result["chained_rows"] == 2
    assert result["unchained_leading"] == 0


def test_tampering_with_a_recorded_decision_is_detected(tmp_path):
    runtime = _allowing_runtime(tmp_path)
    runtime.evaluate(_decision())

    path = runtime.decisions_path
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["actor"] = "agent:someone-else"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    assert RIFRuntime(data_dir=tmp_path).verify_decision_chain()["verified"] is False


def test_audit_summary_reports_chain_state(tmp_path):
    runtime = _allowing_runtime(tmp_path)
    runtime.evaluate(_decision())

    chain = runtime.audit_summary()["decision_chain"]
    assert chain["verified"] is True
    assert chain["chained_rows"] == 1
