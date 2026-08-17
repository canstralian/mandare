"""PostureManager ratchet semantics and shared denial thresholds."""

from rif_runtime.governance.posture import PostureManager, posture_for_denials
from rif_runtime.schemas import Posture


def test_posture_for_denials_thresholds():
    assert posture_for_denials(0) == Posture.normal
    assert posture_for_denials(2) == Posture.normal
    assert posture_for_denials(3) == Posture.elevated
    assert posture_for_denials(9) == Posture.elevated
    assert posture_for_denials(10) == Posture.restricted
    assert posture_for_denials(19) == Posture.restricted
    assert posture_for_denials(20) == Posture.locked


def test_next_posture_ratchets_up_from_normal():
    pm = PostureManager()
    assert pm.next_posture(Posture.normal, 3) == Posture.elevated
    assert pm.next_posture(Posture.elevated, 10) == Posture.restricted
    assert pm.next_posture(Posture.restricted, 20) == Posture.locked


def test_next_posture_never_deescalates_locked_on_partial_window():
    # Regression: absolute threshold mapping used to replace locked with
    # elevated when the rolling window held only 3–9 denials.
    pm = PostureManager()
    assert pm.next_posture(Posture.locked, 5) == Posture.locked
    assert pm.next_posture(Posture.locked, 15) == Posture.locked
    assert pm.next_posture(Posture.restricted, 5) == Posture.restricted


def test_next_posture_keeps_current_when_below_threshold():
    pm = PostureManager()
    assert pm.next_posture(Posture.elevated, 0) == Posture.elevated
    assert pm.next_posture(Posture.locked, 0) == Posture.locked
    assert pm.next_posture(Posture.normal, 0) == Posture.normal
