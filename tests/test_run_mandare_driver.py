"""Smoke test for the run-mandare skill's capability-layer driver.

Runs .claude/skills/run-mandare/drive_capability_layer.py exactly as
documented in SKILL.md and asserts on its stdout, so the skill's documented
claim stays covered by the test suite rather than resting on manual
verification alone.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DRIVER = (
    Path(__file__).resolve().parents[1]
    / ".claude"
    / "skills"
    / "run-mandare"
    / "drive_capability_layer.py"
)


def test_drive_capability_layer_driver_runs_clean() -> None:
    result = subprocess.run(
        [sys.executable, str(DRIVER)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "policy decision: allow" in result.stdout
    assert "execution status: succeeded" in result.stdout
    assert '"payload": "hello from the run-skill driver"' in result.stdout
    assert "policy decision: deny (runtime locked)" in result.stdout
    assert "execution skipped: policy denied" in result.stdout
    assert (
        "CapabilityNotFoundError (expected): Unknown capability: huggingface.infer"
        in result.stdout
    )
