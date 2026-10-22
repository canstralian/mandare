"""Security regressions for the opt-in local workstation status endpoint."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from rif_runtime.api import app
from rif_runtime.auth import ENV_VAR
from rif_runtime.integrations import workstation

client = TestClient(app)
ROUTE = "/v1/workstation/local-status"
HEADER = {"X-API-Key": "correct-key"}


def _enable(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "correct-key")
    monkeypatch.setenv(workstation.ENABLED_VAR, "true")
    monkeypatch.setenv(workstation.TARGET_VAR, "local-lab")


def test_disabled_by_default_and_never_collects(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "correct-key")
    monkeypatch.delenv(workstation.ENABLED_VAR, raising=False)
    monkeypatch.setenv(workstation.TARGET_VAR, "local-lab")

    def forbidden():
        raise AssertionError("collector must not run while disabled")

    monkeypatch.setattr(workstation, "collect_local_status", forbidden)
    assert client.get(ROUTE, headers=HEADER).status_code == 404


def test_requires_control_plane_authentication(monkeypatch):
    _enable(monkeypatch)
    assert client.get(ROUTE).status_code == 401
    assert client.get(ROUTE, headers={"X-API-Key": "wrong"}).status_code == 401


def test_without_configured_keys_fails_closed(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert client.get(ROUTE, headers=HEADER).status_code == 503


def test_rejects_missing_or_unsafe_target_before_collecting(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(
        workstation,
        "collect_local_status",
        lambda: (_ for _ in ()).throw(AssertionError("unexpected collection")),
    )
    for target in ["", "../etc", "/tmp", "a space", "@" * 3, "x" * 65]:
        monkeypatch.setenv(workstation.TARGET_VAR, target)
        assert client.get(ROUTE, headers=HEADER).status_code == 503


def test_minimal_metadata_without_sensitive_inputs(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setenv("PRIVATE_USER_TOKEN", "must-not-leak")
    monkeypatch.setattr(workstation.platform, "system", lambda: "Linux")
    monkeypatch.setattr(workstation.os, "cpu_count", lambda: 12)
    monkeypatch.setattr(
        workstation.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(total=1024, free=256),
    )
    response = client.get(ROUTE, headers=HEADER)
    assert response.status_code == 200
    assert response.json()["target"] == "local-lab"
    assert response.json()["status"] == {
        "os_family": "Linux",
        "python_version": (
            f"{workstation.sys.version_info.major}."
            f"{workstation.sys.version_info.minor}."
            f"{workstation.sys.version_info.micro}"
        ),
        "logical_cpu_count": 12,
        "disk_total_bytes": 1024,
        "disk_free_bytes": 256,
    }
    assert "must-not-leak" not in response.text


def test_collection_failure_is_generic_and_no_data_escapes(monkeypatch):
    _enable(monkeypatch)

    def fail():
        raise OSError("/sensitive/private/path")

    monkeypatch.setattr(workstation, "collect_local_status", fail)
    response = client.get(ROUTE, headers=HEADER)
    assert response.status_code == 503
    assert "/sensitive/private/path" not in response.text
    assert "unavailable" in response.text


def test_unknown_operating_system_is_reduced_to_other(monkeypatch):
    monkeypatch.setattr(workstation.platform, "system", lambda: "SECRET_HOST_INFO")
    monkeypatch.setattr(
        workstation.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(total=100, free=50),
    )
    assert workstation.collect_local_status()["os_family"] == "other"
