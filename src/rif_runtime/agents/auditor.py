from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import cycle guard, types only
    from rif_runtime.runtime import RIFRuntime


class AuditorAgent:
    name = "agent:auditor"

    def audit(self, runtime: "RIFRuntime") -> dict[str, Any]:
        return {
            "agent": self.name,
            **runtime.audit_summary(),
        }
