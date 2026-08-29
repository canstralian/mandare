import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from rif_runtime.resources.discovery import (
    ARDDiscoveryClient,
    DiscoveryIntent,
    ResourceCandidate,
    StaticResourceDiscovery,
)


def candidate(name: str = "Weather") -> ResourceCandidate:
    return ResourceCandidate(
        identifier="urn:air:example.com:server:weather",
        name=name,
        resource_type="application/mcp-server-card+json",
        source="https://registry.example/",
        endpoint="https://example.com/mcp/weather.json",
        capabilities=("WeatherTool",),
        relevance_score=92,
    )


def test_static_discovery_filters_by_type_and_capability() -> None:
    provider = StaticResourceDiscovery([candidate()])

    results = provider.discover(
        DiscoveryIntent(
            objective="get weather",
            resource_types=("application/mcp-server-card+json",),
            required_capabilities=("WeatherTool",),
        )
    )

    assert [result.name for result in results] == ["Weather"]


def test_discovery_score_is_not_trust() -> None:
    result = candidate()

    assert result.relevance_score == 92
    assert result.publisher == "example.com"


class SearchHandler(BaseHTTPRequestHandler):
    request_payload: dict = {}

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        SearchHandler.request_payload = json.loads(self.rfile.read(length))
        body = {
            "results": [
                {
                    "identifier": "urn:air:example.com:server:weather",
                    "displayName": "Weather Data Node",
                    "type": "application/mcp-server-card+json",
                    "url": "https://example.com/mcp/weather.json",
                    "capabilities": ["WeatherTool"],
                    "score": 88,
                    "source": "http://127.0.0.1:0/",
                }
            ]
        }
        encoded = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *_args: object) -> None:
        return


def test_ard_client_maps_search_results() -> None:
    server = HTTPServer(("127.0.0.1", 0), SearchHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = ARDDiscoveryClient(f"http://127.0.0.1:{server.server_port}")
        results = client.discover(
            DiscoveryIntent(
                objective="find weather",
                required_capabilities=("WeatherTool",),
                max_results=5,
            )
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert len(results) == 1
    assert results[0].identifier == "urn:air:example.com:server:weather"
    assert results[0].publisher == "example.com"
    assert results[0].relevance_score == 88
    assert SearchHandler.request_payload == {
        "query": {
            "text": "find weather",
            "filter": {"capabilities": ["WeatherTool"]},
        },
        "pageSize": 5,
    }
