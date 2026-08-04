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
        """Register a capability by its unique name.
        
        Parameters:
        	capability (Capability): The capability to register.
        
        Raises:
        	ValueError: If a capability with the same name is already registered.
        """
        if capability.name in self._capabilities:
            raise ValueError(f"Capability already registered: {capability.name}")

        self._capabilities[capability.name] = capability

    def resolve(self, name: str) -> Capability:
        """Retrieve a registered capability by name.
        
        Parameters:
        	name (str): The unique name of the capability to retrieve.
        
        Returns:
        	Capability: The registered capability.
        
        Raises:
        	CapabilityNotFoundError: If no capability is registered with the given name.
        """
        try:
            return self._capabilities[name]
        except KeyError as exc:
            raise CapabilityNotFoundError(f"Unknown capability: {name}") from exc

    def __contains__(self, name: object) -> bool:
        """Determine whether a capability name is registered.
        
        Parameters:
        	name (object): Value to check against the registered capability names.
        
        Returns:
        	bool: `True` if the value matches a registered capability name, `False` otherwise.
        """
        return name in self._capabilities

    def __len__(self) -> int:
        return len(self._capabilities)
