"""State Controller: the runtime's own posture, mode, and environment.

Holds the state that governance reads and execution cannot write. The kernel
never mutates posture directly — it routes decisions through the existing
`RIFRuntime` governance circuit so the reflexive loop, graph, and decision log
all stay in agreement.

`RIFRuntime` is imported lazily inside the constructor: `runtime.py` imports
the `governance` package, which re-exports `GovernanceEngine`, which reaches
back here. A module-level import would close that cycle.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from .config import load_config
from .intent import Intent
from .schemas import EnvironmentProfile, Posture, RuntimeConfig

if TYPE_CHECKING:  # pragma: no cover - types only
    from .runtime import RIFRuntime


class RuntimeMode(str, Enum):
    """How much latitude the runtime currently grants execution."""

    normal = "normal"
    degraded = "degraded"
    maintenance = "maintenance"
    lockdown = "lockdown"


# Posture drives mode: the runtime narrows itself as it escalates, so mode
# never has to be kept in sync by hand.
POSTURE_MODES: dict[Posture, RuntimeMode] = {
    Posture.normal: RuntimeMode.normal,
    Posture.elevated: RuntimeMode.normal,
    Posture.restricted: RuntimeMode.degraded,
    Posture.locked: RuntimeMode.lockdown,
}


class RuntimeState:
    def __init__(
        self,
        runtime: "RIFRuntime | None" = None,
        config: RuntimeConfig | None = None,
    ) -> None:
        if runtime is None:
            from .runtime import RIFRuntime

            runtime = RIFRuntime()
        self.runtime = runtime
        self.config = config or load_config()

    @property
    def posture(self) -> Posture:
        return self.runtime.posture

    @property
    def environment_name(self) -> str:
        return self.runtime.environment_name

    @property
    def profile(self) -> EnvironmentProfile:
        return self.runtime.profile

    @property
    def mode(self) -> RuntimeMode:
        return POSTURE_MODES.get(self.posture, RuntimeMode.degraded)

    def capture_intent(
        self,
        user_request: str,
        actor: str = "agent:kernel",
        **metadata: str,
    ) -> Intent:
        """Stage 1 of the pipeline: record what arrived, decide nothing."""

        return Intent(actor=actor, request=user_request, metadata=dict(metadata))

    def snapshot(self) -> dict[str, Any]:
        """Environment/posture view pinned into the execution context."""

        profile = self.profile
        return {
            "environment": self.environment_name,
            "posture": self.posture.value,
            "mode": self.mode.value,
            "networking_type": profile.networking_type,
            "allow_mcp_server_network_access": profile.allow_mcp_server_network_access,
            "allow_package_manager_network_access": (
                profile.allow_package_manager_network_access
            ),
            "allowed_hosts": list(profile.allowed_hosts),
        }
