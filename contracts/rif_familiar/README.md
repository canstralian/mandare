# RIF Familiar — Phase 0 Contracts

This directory is the versioned authority boundary for the RIF Familiar / Field Observer v0.1.

## Scope

The device is an ESP32-C5 sensor and local UI node. It is allowed to collect **passive, aggregate** Wi-Fi/BLE context and to transport bounded telemetry only to a local, pinned RIF Edge Relay.

It is not permitted to perform active RF transmission, packet injection, HID execution, IR transmission, remote command execution, or cloud egress.

## Contract set

| Artifact | Purpose |
| --- | --- |
| `capability_manifest.schema.json` | Declares the complete device authority set, relay pinning, and budgets. |
| `observation_event.schema.json` | Defines privacy-redacted, chained passive observation events. |
| `posture_decision.schema.json` | Defines Mandare posture responses consumed by the handheld. |

## Runtime mapping

`mandare.schemas.Posture` remains the sole core posture vocabulary:

- `normal`
- `elevated`
- `restricted`
- `locked`

`offline_safe` is intentionally a **connectivity overlay**, not a new RIF posture. It tells the device to queue locally while retaining the last verified runtime posture. This preserves compatibility with the existing runtime policy and posture model.

The future Edge Relay maps a validated observation to the existing RIF request envelope:

```python
PolicyRequest(
    actor="device:rif-familiar-001",
    action="rf.observe.aggregate",
    target="relay:rif-edge-home",
    reason="passive aggregate observation",
    context={"event_id": "obs_...", "manifest_sha256": "..."},
)
```

The relay must independently enforce device identity, pinned key ID, local-network reachability, payload-size limit, manifest-hash registration, and event-chain continuity before it creates a policy request.

## Contract integrity

Use `python scripts/generate_contract_hashes.py` to generate a SHA-256 receipt for the three schema artifacts. These file hashes are release evidence; a device manifest separately carries its own canonical manifest hash.

## Validation

```bash
pip install -r requirements-dev.txt
pytest -q tests/test_rif_familiar_contracts.py
python scripts/generate_contract_hashes.py
```

Phase 0 closes only after the full CI lane is green and the contract-hash receipt is recorded with the project evidence.
