#!/usr/bin/env python3
"""Generate a deterministic SHA-256 receipt for RIF Familiar schema artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts" / "rif_familiar"
SCHEMA_NAMES = (
    "capability_manifest.schema.json",
    "observation_event.schema.json",
    "posture_decision.schema.json",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    receipt = {
        "receipt_version": "rif-familiar.contract-hashes/v0.1",
        "artifacts": {
            name: sha256_file(CONTRACTS / name)
            for name in SCHEMA_NAMES
        },
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
