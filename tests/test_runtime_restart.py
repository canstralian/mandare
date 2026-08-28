from mandare.config import reset_settings
from mandare.runtime import MandareRuntime
from mandare.schemas import PolicyRequest, Posture


def test_locked_posture_survives_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("RIF_DATA_DIR", str(tmp_path))
    reset_settings()
    try:
        r1 = MandareRuntime()
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
        r2 = MandareRuntime()
        assert r2.posture == Posture.locked
    finally:
        reset_settings()
