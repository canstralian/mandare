from rif_runtime.config import reset_settings
from rif_runtime.replay import ReplayEngine
from rif_runtime.runtime import RIFRuntime
from rif_runtime.schemas import PolicyRequest


def test_replay_engine_uses_rif_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RIF_DATA_DIR", str(tmp_path))
    reset_settings()
    try:
        runtime = RIFRuntime()
        runtime.evaluate(
            PolicyRequest(
                actor="agent:test",
                action="http.request",
                target="https://blocked.example.com",
            )
        )
        assert (tmp_path / "decisions.jsonl").is_file()

        recovered = ReplayEngine().recover()
        assert recovered.historical_decisions == 1
        assert recovered.historical_denials == 1
    finally:
        reset_settings()
