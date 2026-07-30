"""Posture must be monotonic under observation: denial volume raises it, never lowers it."""

import pytest

from rif_runtime.governance.posture import (
    PostureManager,
    escalate_posture,
    next_posture,
    posture_for_denials,
    posture_rank,
)
from rif_runtime.governance.reflexive import ReflexiveLoop
from rif_runtime.governance.telemetry import TelemetryStore
from rif_runtime.schemas import Decision, PolicyDecision, Posture


def _denial(target: str = "https://blocked.example.com") -> PolicyDecision:
    return PolicyDecision(
        decision=Decision.deny,
        actor="agent:test",
        action="http.request",
        target=target,
        environment="RIF_Runtime",
        posture=Posture.normal,
        reason="host denied",
        matched_rule="network.host.denied",
    )


@pytest.mark.parametrize(
    ("denials", "expected"),
    [
        (0, Posture.normal),
        (2, Posture.normal),
        (3, Posture.elevated),
        (9, Posture.elevated),
        (10, Posture.restricted),
        (19, Posture.restricted),
        (20, Posture.locked),
        (500, Posture.locked),
    ],
)
def test_posture_for_denials_thresholds(denials, expected):
    assert posture_for_denials(denials) == expected


@pytest.mark.parametrize("current", list(Posture))
@pytest.mark.parametrize("denials", [0, 2, 3, 9, 10, 19, 20, 100])
def test_next_posture_never_de_escalates(current, denials):
    # Regression: PostureManager used to return the threshold posture outright,
    # so a locked runtime with 3 denials in the window dropped back to elevated
    # -- ordinary denial traffic silently unlocked it.
    result = next_posture(current, denials)
    assert posture_rank(result) >= posture_rank(current)


def test_locked_runtime_stays_locked_under_denial_traffic():
    assert next_posture(Posture.locked, 3) == Posture.locked
    assert next_posture(Posture.locked, 10) == Posture.locked
    assert PostureManager().next_posture(Posture.locked, 3) == Posture.locked


def test_restricted_runtime_is_not_downgraded_to_elevated():
    assert next_posture(Posture.restricted, 3) == Posture.restricted


def test_denials_still_escalate_from_normal():
    assert next_posture(Posture.normal, 3) == Posture.elevated
    assert next_posture(Posture.normal, 10) == Posture.restricted
    assert next_posture(Posture.normal, 20) == Posture.locked


def test_escalate_posture_ladder_is_capped():
    assert escalate_posture(Posture.normal) == Posture.elevated
    assert escalate_posture(Posture.elevated) == Posture.restricted
    assert escalate_posture(Posture.restricted) == Posture.locked
    assert escalate_posture(Posture.locked) == Posture.locked


def test_reflexive_loop_does_not_unlock_a_locked_runtime():
    loop = ReflexiveLoop()
    posture = Posture.locked
    for _ in range(5):
        posture = loop.observe(_denial(), posture)
    assert posture == Posture.locked


def test_reflexive_loop_accepts_injected_collaborators():
    telemetry = TelemetryStore(max_events=10)
    loop = ReflexiveLoop(telemetry=telemetry)
    assert loop.telemetry is telemetry

    posture = Posture.normal
    for _ in range(3):
        posture = loop.observe(_denial(), posture)
    assert posture == Posture.elevated
    assert len(telemetry.events) == 3
