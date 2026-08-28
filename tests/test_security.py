from mandare.security import (
    canonical_json,
    decrypt_text_from_record,
    encrypt_text,
    hash_secret,
    hmac_signature,
    redact_secrets,
    sha256_digest,
    verify_hmac_signature,
    verify_secret,
)


def test_encrypt_decrypt_roundtrip():
    record = encrypt_text("classified", "correct horse battery staple")
    assert (
        decrypt_text_from_record(record, "correct horse battery staple") == "classified"
    )


def test_wrong_passphrase_fails_decryption():
    record = encrypt_text("classified", "right-passphrase")
    try:
        decrypt_text_from_record(record, "wrong-passphrase")
    except ValueError as error:
        assert str(error) == "decryption failed"
    else:
        raise AssertionError("expected decryption failure")


def test_secret_hash_verification():
    record = hash_secret("s3cr3t")
    assert verify_secret("s3cr3t", record)
    assert not verify_secret("wrong", record)


def test_canonical_json_is_stable():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert canonical_json(left) == canonical_json(right)
    assert sha256_digest(left) == sha256_digest(right)


def test_hmac_signature_verification():
    payload = {"decision": "allow", "rule_id": "RIF-001"}
    signature = hmac_signature(payload, "signing-key")
    assert verify_hmac_signature(payload, "signing-key", signature)
    assert not verify_hmac_signature(payload, "wrong-key", signature)


def test_redact_secrets_preserves_safe_hash_fields():
    payload = {
        "api_key": "abc",
        "password": "def",
        "token_hash": "safe",
        "nested": {"authorization": "bearer token"},
    }

    assert redact_secrets(payload) == {
        "api_key": "[REDACTED]",
        "password": "[REDACTED]",
        "token_hash": "safe",
        "nested": {"authorization": "[REDACTED]"},
    }
