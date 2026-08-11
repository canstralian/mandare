"""Smoke tests for deterministic hashing rules used by the replay strategy."""

from __future__ import annotations

import tempfile
from pathlib import Path

from rif_runtime.testing.determinism_strategy import HashingRules, SerializationRules


def test_hash_json_is_key_order_independent() -> None:
    left = HashingRules.hash_json({"b": 2, "a": 1})
    right = HashingRules.hash_json({"a": 1, "b": 2})
    assert left == right
    assert len(left) == 64


def test_hash_json_is_stable_known_value() -> None:
    # Canonical form: {"a":1,"b":2} with separators=(",", ":")
    digest = HashingRules.hash_json({"b": 2, "a": 1})
    assert digest == (
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )


def test_hash_file_normalizes_crlf() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lf = Path(tmp) / "lf.txt"
        crlf = Path(tmp) / "crlf.txt"
        lf.write_bytes(b"line1\nline2\n")
        crlf.write_bytes(b"line1\r\nline2\r\n")
        assert HashingRules.hash_file(str(lf)) == HashingRules.hash_file(str(crlf))


def test_hash_ordered_list_is_order_independent_for_dicts() -> None:
    left = HashingRules.hash_ordered_list([{"b": 2}, {"a": 1}])
    right = HashingRules.hash_ordered_list([{"a": 1}, {"b": 2}])
    assert left == right


def test_serialize_decision_is_compact_and_sorted() -> None:
    payload = {"z": 1, "a": {"y": 2, "x": 3}}
    text = SerializationRules.serialize_decision(payload)
    assert text == '{"a":{"x":3,"y":2},"z":1}'
