import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts" / "rif_familiar"
FIXTURES = ROOT / "fixtures" / "rif_familiar"
FORMAT_CHECKER = FormatChecker()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_name: str) -> Draft202012Validator:
    schema = _load(CONTRACTS / schema_name)
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


def _fixture(fixture_name: str) -> dict[str, Any]:
    return _load(FIXTURES / fixture_name)


def _assert_invalid(validator: Draft202012Validator, value: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        validator.validate(value)


@pytest.mark.parametrize(
    ("schema_name", "fixture_name"),
    [
        ("capability_manifest.schema.json", "valid_manifest.json"),
        ("observation_event.schema.json", "valid_observation.json"),
        ("posture_decision.schema.json", "valid_posture_decision.json"),
    ],
)
def test_valid_contract_fixtures(schema_name: str, fixture_name: str) -> None:
    _validator(schema_name).validate(_fixture(fixture_name))


def test_manifest_rejects_active_rf_transmission() -> None:
    manifest = _fixture("valid_manifest.json")
    manifest["capabilities"]["active_rf_transmission"] = "allow"

    _assert_invalid(_validator("capability_manifest.schema.json"), manifest)


def test_manifest_rejects_unknown_capability() -> None:
    manifest = _fixture("valid_manifest.json")
    manifest["capabilities"]["wireless_beast_mode"] = "allow"

    _assert_invalid(_validator("capability_manifest.schema.json"), manifest)


def test_manifest_requires_tls_and_local_relay() -> None:
    manifest = _fixture("valid_manifest.json")
    manifest["relay_policy"]["hostname"] = "relay.example.com"
    manifest["relay_policy"]["tls_required"] = False

    _assert_invalid(_validator("capability_manifest.schema.json"), manifest)


def test_observation_rejects_raw_identifier() -> None:
    event = _fixture("valid_observation.json")
    event["wireless_summary"]["ssid"] = "not-permitted"

    _assert_invalid(_validator("observation_event.schema.json"), event)


def test_observation_rejects_active_collection_mode() -> None:
    event = _fixture("valid_observation.json")
    event["collection_mode"] = "active_probe"

    _assert_invalid(_validator("observation_event.schema.json"), event)


def test_observation_rejects_invalid_timestamp() -> None:
    event = _fixture("valid_observation.json")
    event["emitted_at"] = "not-a-timestamp"

    _assert_invalid(_validator("observation_event.schema.json"), event)


def test_posture_rejects_offline_safe_as_core_posture() -> None:
    decision = _fixture("valid_posture_decision.json")
    decision["posture"] = "offline_safe"

    _assert_invalid(_validator("posture_decision.schema.json"), decision)


def test_locked_posture_forces_queue_only_transport() -> None:
    decision = _fixture("valid_posture_decision.json")
    decision["posture"] = "locked"
    decision["operating_constraints"] = {
        "scan_interval_seconds": 300,
        "transport_enabled": True,
        "queue_only": False,
    }

    _assert_invalid(_validator("posture_decision.schema.json"), decision)


def test_offline_safe_forces_queue_only_transport() -> None:
    decision = _fixture("valid_posture_decision.json")
    decision["connectivity_state"] = "offline_safe"
    decision["operating_constraints"] = {
        "scan_interval_seconds": 300,
        "transport_enabled": True,
        "queue_only": False,
    }

    _assert_invalid(_validator("posture_decision.schema.json"), decision)


def test_manifest_fixture_can_be_copied_without_mutation() -> None:
    manifest = _fixture("valid_manifest.json")
    copied = copy.deepcopy(manifest)

    assert copied == manifest
