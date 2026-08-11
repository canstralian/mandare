from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..runtime import RIFRuntime


class AuditorAgent:
    name = "agent:auditor"

    def audit(self, runtime: "RIFRuntime") -> dict[str, Any]:
        return {
            "agent": self.name,
            **runtime.audit_summary(),
        }
