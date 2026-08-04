from __future__ import annotations

from collections.abc import Iterable

from rif_runtime.execution.exceptions import CapabilityNotFoundError

from .capability import Capability


class CapabilityRegistry:
    """
    Registry of executable capabilities.

    Capability names are unique.
    Registration is explicit.
    Resolution is deterministic.
    """

    def __init__(self, capabilities: Iterable[Capability] | None = None) -> None:
        self._capabilities: dict[str, Capability] = {}

        if capabilities is not None:
            for capability in capabilities:
                self.register(capability)

    def register(self, capability: Capability) -> None:
        if capability.name in self._capabilities:
            raise ValueError(f"Capability already registered: {capability.name}")

        self._capabilities[capability.name] = capability

    def resolve(self, name: str) -> Capability:
        try:
            return self._capabilities[name]
        except KeyError as exc:
            raise CapabilityNotFoundError(f"Unknown capability: {name}") from exc

    def __contains__(self, name: object) -> bool:
        return name in self._capabilities

    def __len__(self) -> int:
        return len(self._capabilities)
