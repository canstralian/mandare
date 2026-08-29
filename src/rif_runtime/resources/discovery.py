from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ResourceDiscoveryError(RuntimeError):
    """Raised when a discovery provider cannot return usable results."""


@dataclass(frozen=True, slots=True)
class DiscoveryIntent:
    """Search intent passed to resource discovery providers."""

    objective: str
    resource_types: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    max_results: int = 10

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("discovery objective must not be empty")
        if not 1 <= self.max_results <= 100:
            raise ValueError("max_results must be between 1 and 100")


@dataclass(frozen=True, slots=True)
class ResourceCandidate:
    """A discoverable resource, before governance authorization."""

    identifier: str
    name: str
    resource_type: str
    source: str
    endpoint: str | None = None
    capabilities: tuple[str, ...] = ()
    representative_queries: tuple[str, ...] = ()
    publisher: str | None = None
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("resource identifier must not be empty")
        if not self.name.strip():
            raise ValueError("resource name must not be empty")
        if not self.resource_type.strip():
            raise ValueError("resource type must not be empty")
        if not self.source.strip():
            raise ValueError("resource source must not be empty")
        if self.relevance_score is not None and not 0 <= self.relevance_score <= 100:
            raise ValueError("relevance_score must be between 0 and 100")


class ResourceDiscovery(Protocol):
    """Provider-neutral discovery interface used by the runtime."""

    def discover(self, intent: DiscoveryIntent) -> list[ResourceCandidate]:
        ...


class StaticResourceDiscovery:
    """Deterministic local discovery provider for tests and offline deployments."""

    def __init__(self, candidates: list[ResourceCandidate] | tuple[ResourceCandidate, ...]):
        self._candidates = tuple(candidates)

    def discover(self, intent: DiscoveryIntent) -> list[ResourceCandidate]:
        results = [
            candidate
            for candidate in self._candidates
            if not intent.resource_types or candidate.resource_type in intent.resource_types
        ]
        if intent.required_capabilities:
            required = set(intent.required_capabilities)
            results = [
                candidate
                for candidate in results
                if required.issubset(candidate.capabilities)
            ]
        return list(results[: intent.max_results])


class ARDDiscoveryClient:
    """Minimal ARD v0.91 search client.

    ARD is used only for discovery. Returned relevance scores are preserved as
    informational search signals and are never interpreted as trust or policy
    authorization.
    """

    def __init__(self, endpoint: str, timeout: float = 10.0):
        if not endpoint.startswith(("https://", "http://")):
            raise ValueError("ARD endpoint must use http:// or https://")
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def discover(self, intent: DiscoveryIntent) -> list[ResourceCandidate]:
        filters: dict[str, list[str]] = {}
        if intent.resource_types:
            filters["type"] = list(intent.resource_types)
        if intent.required_capabilities:
            filters["capabilities"] = list(intent.required_capabilities)

        payload: dict[str, Any] = {
            "query": {"text": intent.objective},
            "pageSize": intent.max_results,
        }
        if filters:
            payload["query"]["filter"] = filters

        request = Request(
            f"{self.endpoint}/search",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ResourceDiscoveryError(f"ARD discovery failed: {exc}") from exc

        raw_results = body.get("results", [])
        if not isinstance(raw_results, list):
            raise ResourceDiscoveryError("ARD response field 'results' must be an array")

        return [self._candidate(item) for item in raw_results[: intent.max_results]]

    def _candidate(self, item: dict[str, Any]) -> ResourceCandidate:
        if not isinstance(item, dict):
            raise ResourceDiscoveryError("ARD result must be an object")
        identifier = item.get("identifier")
        name = item.get("displayName", identifier)
        resource_type = item.get("type")
        source = item.get("source", self.endpoint)
        if not all(isinstance(value, str) and value for value in (identifier, name, resource_type, source)):
            raise ResourceDiscoveryError("ARD result is missing required identity fields")

        score = item.get("score")
        if score is not None and not isinstance(score, (int, float)):
            raise ResourceDiscoveryError("ARD result score must be numeric")

        return ResourceCandidate(
            identifier=identifier,
            name=name,
            resource_type=resource_type,
            source=source,
            endpoint=item.get("url"),
            capabilities=tuple(item.get("capabilities", ())),
            representative_queries=tuple(item.get("representativeQueries", ())),
            publisher=_publisher_from_identifier(identifier),
            relevance_score=float(score) if score is not None else None,
            metadata=item,
        )


def _publisher_from_identifier(identifier: str) -> str | None:
    """Extract the publisher segment from an ARD URN without asserting trust."""
    parts = identifier.split(":", 3)
    return parts[2] if len(parts) == 4 and parts[0] == "urn" and parts[1] == "air" else None
