"""Isolated execution of a candidate solution against a task's assertion tests."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class SandboxResult:
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


def _render_test_module(tests: list[str]) -> str:
    lines = ["from candidate import *  # noqa: F401,F403", ""]
    for index, assertion in enumerate(tests):
        lines.append(f"def test_assertion_{index}():")
        lines.append(f"    {assertion}")
        lines.append("")
    return "\n".join(lines)


def run_in_sandbox(
    code: str,
    tests: list[str],
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> SandboxResult:
    """Write `code` and `tests` into an isolated temp dir and run pytest against them.

    Each entry in `tests` is a standalone assertion string (e.g.
    "assert is_palindrome('hello') is False"), executed as its own pytest
    test function against whatever the candidate module exports.
    """
    with tempfile.TemporaryDirectory(prefix="rif_eval_") as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "candidate.py").write_text(code, encoding="utf-8")
        (tmp_path / "test_candidate.py").write_text(
            _render_test_module(tests), encoding="utf-8"
        )

        try:
            proc = subprocess.run(  # noqa: S603
                [sys.executable, "-m", "pytest", "-q", "test_candidate.py"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            return SandboxResult(
                passed=False,
                exit_code=-1,
                stdout=error.stdout or "",
                stderr=f"sandbox execution timed out after {timeout}s",
                timed_out=True,
            )

        return SandboxResult(
            passed=proc.returncode == 0,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
