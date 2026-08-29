from pathlib import Path

from rif_runtime.resources.discovery import DiscoveryIntent, ResourceCandidate, StaticResourceDiscovery
from rif_runtime.runtime import RIFRuntime


def test_runtime_discovery_is_observation_not_authorization(tmp_path: Path) -> None:
    runtime = RIFRuntime(data_dir=tmp_path)
    runtime.set_resource_discovery(
        StaticResourceDiscovery(
            [
                ResourceCandidate(
                    identifier="urn:air:example.com:server:weather",
                    name="Weather Data Node",
                    resource_type="application/mcp-server-card+json",
                    source="local-test",
                    capabilities=("WeatherTool",),
                    relevance_score=99,
                )
            ]
        )
    )

    results = runtime.discover_resources(
        DiscoveryIntent(objective="current weather", max_results=1)
    )

    assert len(results) == 1
    assert results[0].relevance_score == 99
    assert not (tmp_path / "capability_evidence.jsonl").exists()
    assert (tmp_path / "discovery_evidence.jsonl").exists()
