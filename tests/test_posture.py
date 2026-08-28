from mandare.governance.posture import PostureManager, posture_for_denials
from mandare.replay import ReplayEngine
from mandare.runtime import MandareRuntime
from mandare.schemas import PolicyRequest, Posture


def test_posture_for_denials_thresholds():
    assert posture_for_denials(0) == Posture.normal
    assert posture_for_denials(2) == Posture.normal
    assert posture_for_denials(3) == Posture.elevated
    assert posture_for_denials(9) == Posture.elevated
    assert posture_for_denials(10) == Posture.restricted
    assert posture_for_denials(19) == Posture.restricted
    assert posture_for_denials(20) == Posture.locked


def test_next_posture_escalates_from_normal():
    pm = PostureManager()
    assert pm.next_posture(Posture.normal, 2) == Posture.normal
    assert pm.next_posture(Posture.normal, 3) == Posture.elevated
    assert pm.next_posture(Posture.elevated, 10) == Posture.restricted
    assert pm.next_posture(Posture.restricted, 20) == Posture.locked


def test_next_posture_never_deescalates_via_denials():
    """Denial thresholds must not drop an operator-restored high posture."""
    pm = PostureManager()
    assert pm.next_posture(Posture.locked, 3) == Posture.locked
    assert pm.next_posture(Posture.locked, 10) == Posture.locked
    assert pm.next_posture(Posture.locked, 19) == Posture.locked
    assert pm.next_posture(Posture.restricted, 3) == Posture.restricted
    assert pm.next_posture(Posture.restricted, 9) == Posture.restricted
    assert pm.next_posture(Posture.elevated, 2) == Posture.elevated


def test_replay_posture_from_denials_matches_shared_helper(tmp_path):
    engine = ReplayEngine(tmp_path / "decisions.jsonl")
    for n in (0, 2, 3, 10, 20):
        assert engine._posture_from_denials(n) == posture_for_denials(n)


def test_restored_locked_stays_locked_after_three_denials(tmp_path):
    first = MandareRuntime(data_dir=tmp_path)
    first.set_posture(Posture.locked)
    restarted = MandareRuntime(data_dir=tmp_path)
    assert restarted.posture == Posture.locked
    for i in range(3):
        restarted.evaluate(
            PolicyRequest(
                actor="agent:test",
                action="http.request",
                target=f"https://evil{i}.example.com",
            )
        )
    assert restarted.posture == Posture.locked


def test_restored_restricted_stays_restricted_after_three_denials(tmp_path):
    first = MandareRuntime(data_dir=tmp_path)
    first.set_posture(Posture.restricted)
    restarted = MandareRuntime(data_dir=tmp_path)
    assert restarted.posture == Posture.restricted
    for i in range(3):
        restarted.evaluate(
            PolicyRequest(
                actor="agent:test",
                action="http.request",
                target=f"https://evil{i}.example.com",
            )
        )
    assert restarted.posture == Posture.restricted


def test_operator_set_posture_still_deescalates(tmp_path):
    runtime = MandareRuntime(data_dir=tmp_path)
    runtime.set_posture(Posture.locked)
    runtime.set_posture(Posture.normal)
    assert runtime.posture == Posture.normal
