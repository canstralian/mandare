from datetime import datetime, timezone
from uuid import uuid4

import pytest

from rif_runtime.security import (
    canonical_json,
    decrypt_text,
    decrypt_text_from_record,
    encrypt_text,
    hash_secret,
    hmac_signature,
    redact_secrets,
    sha256_digest,
    verify_hmac_signature,
    verify_secret,
)


def test_encrypt_and_decrypt_text_round_trip():
    encrypted = encrypt_text("governed secret", "correct horse battery staple")

    assert decrypt_text_from_record(encrypted, "correct horse battery staple") == "governed secret"


def test_decrypt_rejects_wrong_passphrase():
    encrypted = encrypt_text("governed secret", "right-passphrase")

    with pytest.raises(ValueError):
        decrypt_text(
            str(encrypted["ciphertext"]),
            "wrong-passphrase",
            str(encrypted["salt"]),
            int(encrypted["iterations"]),
        )


def test_encrypt_text_uses_random_nonce():
    first = encrypt_text("same plaintext", "same passphrase")
    second = encrypt_text("same plaintext", "same passphrase")

    assert first["ciphertext"] != second["ciphertext"]


def test_decrypt_uses_stored_iterations():
    encrypted = encrypt_text("iteration-sensitive", "passphrase", iterations=100_000)

    assert decrypt_text_from_record(encrypted, "passphrase") == "iteration-sensitive"


def test_salted_secret_hash_verifies_without_storing_plaintext():
    record = hash_secret("runtime-token")

    assert verify_secret("runtime-token", record)
    assert not verify_secret("wrong-token", record)
    assert record["digest"] != "runtime-token"


def test_canonical_hash_is_stable_for_dict_order():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}

    assert sha256_digest(left) == sha256_digest(right)


def test_canonical_json_normalizes_known_types():
    payload = {
        "id": uuid4(),
        "created": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "blob": b"rif",
    }

    encoded = canonical_json(payload)

    assert "2026-01-01T00:00:00+00:00" in encoded


def test_canonical_json_rejects_unknown_types():
    class Unsupported:
        pass

    with pytest.raises(TypeError):
        canonical_json({"bad": Unsupported()})


def test_hmac_signature_verification():
    payload = {"decision": "deny", "matched_rule": "network.host.denied"}
    signature = hmac_signature(payload, "audit-key")

    assert verify_hmac_signature(payload, "audit-key", signature)
    assert not verify_hmac_signature(payload, "wrong-key", signature)


def test_redact_secrets_recursively_and_preserves_hashes():
    payload = {
        "Authorization": "Bearer abc",
        "x-api-key": "xyz",
        "openai_api_key": "key",
        "token_hash": "safe-hash",
        "nested": {
            "password": "bad",
            "safe": "visible",
        },
    }

    assert redact_secrets(payload) == {
        "Authorization": "[REDACTED]",
        "x-api-key": "[REDACTED]",
        "openai_api_key": "[REDACTED]",
        "token_hash": "safe-hash",
        "nested": {
            "password": "[REDACTED]",
            "safe": "visible",
        },
    }
