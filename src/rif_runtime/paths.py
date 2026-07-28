"""Resolution of the runtime's on-disk state directory.

All persisted state (decision log, posture history, evidence, policy rules)
lives under one directory, ``data/`` by default. Setting ``RIF_DATA_DIR``
relocates the whole set — which is how the test suite keeps its writes out of
the repository's checked-in ``data/policies.json`` and gitignored JSONL logs.

Resolved per call rather than at import, so a process that sets the variable
before constructing a runtime gets the directory it asked for.
"""

from __future__ import annotations

import os
from pathlib import Path

DATA_DIR_ENV = "RIF_DATA_DIR"
DEFAULT_DATA_DIR = Path("data")

DECISIONS_FILE = "decisions.jsonl"
POSTURE_HISTORY_FILE = "posture_history.jsonl"
EVIDENCE_FILE = "metasploit_evidence.jsonl"
POLICIES_FILE = "policies.json"


def data_dir() -> Path:
    configured = os.getenv(DATA_DIR_ENV)
    return Path(configured) if configured else DEFAULT_DATA_DIR


def data_path(name: str) -> Path:
    return data_dir() / name
