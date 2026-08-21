"""Reflexive governance loop with startup replay capability.

The ``ReflexiveLoop`` observes decisions and adjusts posture in real time.
The ``restore_from_log`` function replays a persisted decision log at startup
to recover the last-known posture state after a runtime restart.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..schemas import PolicyDecision, Posture
from .posture import PostureManager, PostureThresholds
from .telemetry import TelemetryStore, emit_metric

logger = logging.getLogger(__name__)


class ReflexiveLoop:
    """Observes policy decisions and adjusts governance posture."""

    def __init__(self, thresholds: PostureThresholds | None = None) -> None:
        self.telemetry = TelemetryStore()
        self.posture_manager = PostureManager(thresholds)

    def observe(self, decision: PolicyDecision, current_posture: Posture) -> Posture:
        """Record a decision and return the updated posture level."""
        self.telemetry.record(decision)
        denials = self.telemetry.denial_count(minutes=60)
        return self.posture_manager.next_posture(current_posture, denials)


def restore_from_log(
    decision_log_path: Path,
    thresholds: PostureThresholds | None = None,
) -> Posture:
    """Replay decision log at startup to recover last posture state.

    Reads a JSONL file where each line is a decision record with at least
    a ``"decision"`` field (``"allow"`` or ``"deny"``). Replays all entries
    through the PostureManager to compute the final posture.

    Args:
        decision_log_path: Path to the JSONL decision log file.
        thresholds: Optional posture thresholds (uses defaults if None).

    Returns:
        The recovered posture level. Returns ``Posture.normal`` if the log
        does not exist (fresh install).
    """
    if not decision_log_path.is_file():
        return Posture.normal

    posture_manager = PostureManager(thresholds)
    current_posture = Posture.normal
    denial_count = 0
    total_replayed = 0

    with open(decision_log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("decision") == "deny":
                denial_count += 1
            total_replayed += 1
            current_posture = posture_manager.next_posture(
                current_posture, denial_count
            )

    emit_metric(
        "rif.governance.replay_completed",
        1.0,
        {
            "decisions_replayed": str(total_replayed),
            "final_posture": current_posture.value,
            "denials": str(denial_count),
        },
    )
    logger.info(
        "Governance state restored: %d decisions replayed, final posture=%s",
        total_replayed,
        current_posture.value,
    )
    return current_posture
