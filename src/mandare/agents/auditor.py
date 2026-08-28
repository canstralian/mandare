from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..runtime import MandareRuntime


class AuditorAgent:
    name = "agent:auditor"

    def audit(self, runtime: "MandareRuntime") -> dict[str, Any]:
        return {
            "agent": self.name,
            **runtime.audit_summary(),
        }
