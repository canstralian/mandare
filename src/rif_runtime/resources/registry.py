from __future__ import annotations

from collections.abc import Iterable

from .descriptor import ResourceCapabilityDescriptor
from .exceptions import (
    DuplicateResourceCapabilityError,
    UnknownResourceCapabilityError,
)


class ResourceCapabilityRegistry:
    """
    Registry of governed resource capability descriptors.

    Registration is explicit.
    Resolution is deterministic.
    """

    def __init__(
        self,
        capabilities: Iterable[ResourceCapabilityDescriptor] | None = None,
    ) -> None:
        self._capabilities: dict[str, ResourceCapabilityDescriptor] = {}

        if capabilities is not None:
            for capability in capabilities:
                self.register(capability)

    def register(
        self,
        capability: ResourceCapabilityDescriptor,
    ) -> None:
        if capability.name in self._capabilities:
            raise DuplicateResourceCapabilityError(
                f"Duplicate resource capability: {capability.name}"
            )

        self._capabilities[capability.name] = capability

    def resolve(
        self,
        name: str,
    ) -> ResourceCapabilityDescriptor:
        try:
            return self._capabilities[name]
        except KeyError as exc:
            raise UnknownResourceCapabilityError(
                f"Unknown resource capability: {name}"
            ) from exc

    def contains(self, name: str) -> bool:
        return name in self._capabilities

    def list(self) -> tuple[ResourceCapabilityDescriptor, ...]:
        return tuple(self._capabilities.values())

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._capabilities

    def __len__(self) -> int:
        return len(self._capabilities)
