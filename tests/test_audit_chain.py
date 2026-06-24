from dataclasses import replace

from rif_runtime.audit import GENESIS_HASH, append_record, verify_chain


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
