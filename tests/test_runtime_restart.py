from rif_runtime.config import reset_settings
from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import PolicyRequest, Posture


def test_locked_posture_survives_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("RIF_DATA_DIR", str(tmp_path))
    reset_settings()
    try:
        r1 = RIFRuntime()
        req = PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="evil.com",
        )
        for _ in range(20):
            r1.evaluate(req)
        assert r1.posture == Posture.locked

        # Simulate a restart: clear the settings cache and build a fresh runtime
        # backed by the same data directory.
        reset_settings()
        r2 = RIFRuntime()
        assert r2.posture == Posture.locked
    finally:
        reset_settings()


def test_control_plane_posture_reset_survives_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("RIF_DATA_DIR", str(tmp_path))
    reset_settings()
    try:
        r1 = RIFRuntime()
        req = PolicyRequest(
            actor="agent:test",
            action="http.request",
            target="evil.com",
        )
        for _ in range(5):
            r1.evaluate(req)
        assert r1.posture == Posture.elevated

        # Control-plane reset must append posture_history so restart matches.
        r1.set_posture(Posture.normal)
        assert r1.posture == Posture.normal
        assert r1.posture_store.count() >= 2

        reset_settings()
        r2 = RIFRuntime()
        assert r2.posture == Posture.normal
    finally:
        reset_settings()


def test_control_plane_set_posture_survives_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("RIF_DATA_DIR", str(tmp_path))
    reset_settings()
    try:
        r1 = RIFRuntime()
        r1.set_posture(Posture.restricted)
        assert r1.posture == Posture.restricted

        reset_settings()
        r2 = RIFRuntime()
        assert r2.posture == Posture.restricted
    finally:
        reset_settings()
