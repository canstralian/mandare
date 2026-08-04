"""Enterprise governance layer tests.

Validates:
- Configurable posture thresholds
- Startup auto-replay from decision log
- Thread-safe telemetry counters
- Structured metric log line format
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rif_runtime.governance.posture import PostureManager, PostureThresholds
from rif_runtime.governance.reflexive import ReflexiveLoop, restore_from_log
from rif_runtime.governance.telemetry import MetricsRegistry, TelemetryStore, emit_metric, metrics
from rif_runtime.schemas import PolicyDecision, Posture


# ---------------------------------------------------------------------------
# Posture threshold tests
# ---------------------------------------------------------------------------


class TestPostureThresholds:
    """Posture escalation respects configurable thresholds."""

    def test_default_thresholds_match_original_behaviour(self) -> None:
        """Default thresholds reproduce the original hardcoded logic."""
        mgr = PostureManager()
        assert mgr.next_posture(Posture.normal, 2) == Posture.normal
        assert mgr.next_posture(Posture.normal, 3) == Posture.elevated
        assert mgr.next_posture(Posture.normal, 10) == Posture.restricted
        assert mgr.next_posture(Posture.normal, 20) == Posture.locked

    def test_custom_thresholds_elevated(self) -> None:
        """Custom elevated_at threshold is respected."""
        thresholds = PostureThresholds(elevated_at=5, restricted_at=15, locked_at=25)
        mgr = PostureManager(thresholds)
        # Below custom threshold - no escalation
        assert mgr.next_posture(Posture.normal, 4) == Posture.normal
        # At custom threshold - escalates
        assert mgr.next_posture(Posture.normal, 5) == Posture.elevated

    def test_custom_thresholds_restricted(self) -> None:
        """Custom restricted_at threshold is respected."""
        thresholds = PostureThresholds(elevated_at=2, restricted_at=8, locked_at=30)
        mgr = PostureManager(thresholds)
        assert mgr.next_posture(Posture.normal, 7) == Posture.elevated
        assert mgr.next_posture(Posture.normal, 8) == Posture.restricted

    def test_custom_thresholds_locked(self) -> None:
        """Custom locked_at threshold is respected."""
        thresholds = PostureThresholds(elevated_at=1, restricted_at=5, locked_at=10)
        mgr = PostureManager(thresholds)
        assert mgr.next_posture(Posture.normal, 9) == Posture.restricted
        assert mgr.next_posture(Posture.normal, 10) == Posture.locked

    def test_thresholds_property_accessible(self) -> None:
        """PostureManager exposes thresholds via property."""
        t = PostureThresholds(elevated_at=7, restricted_at=14, locked_at=28)
        mgr = PostureManager(t)
        assert mgr.thresholds.elevated_at == 7
        assert mgr.thresholds.restricted_at == 14
        assert mgr.thresholds.locked_at == 28

    def test_reflexive_loop_uses_custom_thresholds(self) -> None:
        """ReflexiveLoop forwards thresholds to its PostureManager."""
        t = PostureThresholds(elevated_at=5, restricted_at=15, locked_at=25)
        loop = ReflexiveLoop(thresholds=t)
        assert loop.posture_manager.thresholds == t


# ---------------------------------------------------------------------------
# Auto-replay tests
# ---------------------------------------------------------------------------


class TestAutoReplay:
    """Startup replay restores correct posture from decision log."""

    def _write_decision_log(self, tmp: Path, decisions: list[str]) -> None:
        """Write a JSONL decision log fixture."""
        with open(tmp, "w", encoding="utf-8") as f:
            for d in decisions:
                record = {
                    "decision": d,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "policy": "test",
                }
                f.write(json.dumps(record) + "\n")

    def test_replay_empty_log_returns_normal(self, tmp_path: Path) -> None:
        """An empty log results in normal posture."""
        log_path = tmp_path / "decisions.jsonl"
        log_path.write_text("")
        assert restore_from_log(log_path) == Posture.normal

    def test_replay_missing_log_returns_normal(self, tmp_path: Path) -> None:
        """A non-existent log (fresh install) returns normal posture."""
        log_path = tmp_path / "nonexistent.jsonl"
        assert restore_from_log(log_path) == Posture.normal

    def test_replay_reaches_elevated(self, tmp_path: Path) -> None:
        """3 denials in log -> elevated posture."""
        log_path = tmp_path / "decisions.jsonl"
        self._write_decision_log(log_path, ["deny", "deny", "deny"])
        assert restore_from_log(log_path) == Posture.elevated

    def test_replay_reaches_restricted(self, tmp_path: Path) -> None:
        """10 denials in log -> restricted posture."""
        log_path = tmp_path / "decisions.jsonl"
        self._write_decision_log(log_path, ["deny"] * 10)
        assert restore_from_log(log_path) == Posture.restricted

    def test_replay_reaches_locked(self, tmp_path: Path) -> None:
        """20 denials in log -> locked posture."""
        log_path = tmp_path / "decisions.jsonl"
        self._write_decision_log(log_path, ["deny"] * 20)
        assert restore_from_log(log_path) == Posture.locked

    def test_replay_mixed_decisions(self, tmp_path: Path) -> None:
        """Mixed allow/deny decisions yield correct count."""
        log_path = tmp_path / "decisions.jsonl"
        # 5 denials among allows -> elevated (threshold 3)
        decisions = ["allow", "deny", "allow", "deny", "deny", "allow", "deny", "deny"]
        self._write_decision_log(log_path, decisions)
        assert restore_from_log(log_path) == Posture.elevated

    def test_replay_with_custom_thresholds(self, tmp_path: Path) -> None:
        """Replay respects custom thresholds."""
        log_path = tmp_path / "decisions.jsonl"
        self._write_decision_log(log_path, ["deny"] * 5)
        thresholds = PostureThresholds(elevated_at=10, restricted_at=20, locked_at=30)
        # 5 denials but threshold is 10, so still normal
        assert restore_from_log(log_path, thresholds) == Posture.normal

    def test_replay_skips_malformed_lines(self, tmp_path: Path) -> None:
        """Malformed JSON lines are skipped gracefully."""
        log_path = tmp_path / "decisions.jsonl"
        with open(log_path, "w") as f:
            f.write("not json\n")
            f.write('{"decision": "deny"}\n')
            f.write("also broken {{\n")
            f.write('{"decision": "deny"}\n')
            f.write('{"decision": "deny"}\n')
        # 3 valid denials -> elevated
        assert restore_from_log(log_path) == Posture.elevated


# ---------------------------------------------------------------------------
# Telemetry tests
# ---------------------------------------------------------------------------


class TestTelemetryMetrics:
    """Telemetry counters increment correctly under concurrent load."""

    def test_emit_metric_valid_json(self, caplog: pytest.LogCaptureFixture) -> None:
        """emit_metric produces valid JSON log lines."""
        with caplog.at_level(logging.INFO, logger="rif_runtime.governance.telemetry"):
            emit_metric("rif.test.metric", 42.0, {"env": "test"})

        assert len(caplog.records) == 1
        data = json.loads(caplog.records[0].getMessage())
        assert data["metric"] == "rif.test.metric"
        assert data["value"] == 42.0
        assert data["tags"]["env"] == "test"
        assert "ts" in data
        # Validate ts is ISO format
        datetime.fromisoformat(data["ts"])

    def test_metrics_registry_increment(self) -> None:
        """MetricsRegistry.increment atomically updates counters."""
        registry = MetricsRegistry()
        registry.increment("rif.decisions.total", 1.0)
        registry.increment("rif.decisions.total", 1.0)
        registry.increment("rif.decisions.denied", 1.0)
        assert registry.get("rif.decisions.total") == 2.0
        assert registry.get("rif.decisions.denied") == 1.0
        assert registry.get("rif.decisions.allowed") == 0.0

    def test_metrics_registry_thread_safety(self) -> None:
        """Counters are correct after concurrent increments."""
        registry = MetricsRegistry()
        num_threads = 10
        increments_per_thread = 100

        def worker() -> None:
            for _ in range(increments_per_thread):
                registry.increment("rif.decisions.total", 1.0)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = float(num_threads * increments_per_thread)
        assert registry.get("rif.decisions.total") == expected

    def test_metrics_registry_reset(self) -> None:
        """Reset clears all counters."""
        registry = MetricsRegistry()
        registry.increment("rif.decisions.total", 5.0)
        registry.reset()
        assert registry.get("rif.decisions.total") == 0.0

    def test_metrics_registry_snapshot(self) -> None:
        """Snapshot returns a copy of all counters."""
        registry = MetricsRegistry()
        registry.increment("a", 1.0)
        registry.increment("b", 2.0)
        snap = registry.snapshot()
        assert snap == {"a": 1.0, "b": 2.0}

    def test_record_latency(self) -> None:
        """record_latency accumulates latency values."""
        registry = MetricsRegistry()
        registry.record_latency("rif.policy.eval_latency_ms", 12.5)
        registry.record_latency("rif.policy.eval_latency_ms", 7.5)
        assert registry.get("rif.policy.eval_latency_ms") == 20.0

    def test_structured_log_lines_are_valid_json(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """All metric emissions produce parseable JSON."""
        registry = MetricsRegistry()
        with caplog.at_level(logging.INFO, logger="rif_runtime.governance.telemetry"):
            registry.increment("rif.decisions.total", 1.0, {"action": "tool_call"})
            registry.increment("rif.decisions.denied", 1.0, {"reason": "policy"})
            registry.record_latency(
                "rif.policy.eval_latency_ms", 5.2, {"policy": "default"}
            )

        for record in caplog.records:
            data = json.loads(record.getMessage())
            assert "metric" in data
            assert "value" in data
            assert "tags" in data
            assert "ts" in data
