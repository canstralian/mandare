from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken

DEFAULT_PBKDF2_ITERATIONS = int(os.getenv("RIF_PBKDF2_ITERATIONS", "600000"))
REDACT_SUBSTRINGS = ("api_key", "apikey", "authorization", "password", "secret", "token")
SAFE_SUFFIXES = ("_hash", "_digest", "_id")


def random_salt(length: int = 32) -> bytes:
    return secrets.token_bytes(length)


def encode_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode()


def decode_bytes(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode())


def derive_fernet_key(passphrase: str, salt: bytes, iterations: int = DEFAULT_PBKDF2_ITERATIONS) -> bytes:
    raw = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, iterations, dklen=32)
    return base64.urlsafe_b64encode(raw)


def encrypt_text(plaintext: str, passphrase: str, salt: bytes | None = None, iterations: int = DEFAULT_PBKDF2_ITERATIONS) -> dict[str, str | int]:
    actual_salt = salt or random_salt()
    key = derive_fernet_key(passphrase, actual_salt, iterations)
    ciphertext = Fernet(key).encrypt(plaintext.encode()).decode()
    return {"ciphertext": ciphertext, "salt": encode_bytes(actual_salt), "kdf": "pbkdf2_hmac_sha256", "iterations": iterations}


def decrypt_text(ciphertext: str, passphrase: str, salt_b64: str, iterations: int = DEFAULT_PBKDF2_ITERATIONS) -> str:
    key = derive_fernet_key(passphrase, decode_bytes(salt_b64), iterations)
    try:
        return Fernet(key).decrypt(ciphertext.encode()).decode()
    except InvalidToken as error:
        raise ValueError("decryption failed") from error


def decrypt_text_from_record(record: dict[str, str | int], passphrase: str) -> str:
    return decrypt_text(str(record["ciphertext"]), passphrase, str(record["salt"]), int(record["iterations"]))


def hash_secret(secret: str, salt: bytes | None = None, iterations: int = DEFAULT_PBKDF2_ITERATIONS) -> dict[str, str | int]:
    actual_salt = salt or random_salt()
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), actual_salt, iterations)
    return {"algorithm": "pbkdf2_hmac_sha256", "iterations": iterations, "salt": encode_bytes(actual_salt), "digest": encode_bytes(digest)}


def verify_secret(secret: str, record: dict[str, str | int]) -> bool:
    salt = decode_bytes(str(record["salt"]))
    expected = str(record["digest"])
    candidate = hash_secret(secret, salt=salt, iterations=int(record["iterations"]))["digest"]
    return hmac.compare_digest(str(candidate), expected)


def normalize_for_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): normalize_for_json(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_for_json(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, bytes):
        return encode_bytes(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported canonical JSON type: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(normalize_for_json(value), sort_keys=True, separators=(",", ":"))


def sha256_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def hmac_signature(value: Any, key: str) -> str:
    return hmac.new(key.encode(), canonical_json(value).encode(), hashlib.sha256).hexdigest()


def verify_hmac_signature(value: Any, key: str, signature: str) -> bool:
    return hmac.compare_digest(hmac_signature(value, key), signature)


def should_redact_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized.endswith(SAFE_SUFFIXES):
        return False
    return any(fragment in normalized for fragment in REDACT_SUBSTRINGS)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if should_redact_key(str(key)) else redact_secrets(inner)
            for key, inner in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_secrets(item) for item in value]
    return value
