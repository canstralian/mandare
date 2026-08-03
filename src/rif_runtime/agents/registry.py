from __future__ import annotations

from collections.abc import Iterable

from .exceptions import (
    DuplicateAgentError,
    UnknownAgentError,
)
from .manifest import AgentManifest


class AgentRegistry:
    """
    Deterministic registry of agent manifests.
    """

    def __init__(
        self,
        manifests: Iterable[AgentManifest] | None = None,
    ) -> None:
        self._manifests: dict[str, AgentManifest] = {}

        if manifests is not None:
            for manifest in manifests:
                self.register(manifest)

    def register(self, manifest: AgentManifest) -> None:
        if manifest.name in self._manifests:
            raise DuplicateAgentError(
                f"Agent already registered: {manifest.name}"
            )

        self._manifests[manifest.name] = manifest

    def resolve(self, name: str) -> AgentManifest:
        try:
            return self._manifests[name]
        except KeyError as exc:
            raise UnknownAgentError(
                f"Unknown agent: {name}"
            ) from exc

    def contains(self, name: object) -> bool:
        return name in self._manifests

    def __contains__(self, name: object) -> bool:
        return self.contains(name)

    def __len__(self) -> int:
        return len(self._manifests)
