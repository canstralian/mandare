from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..runtime import RIFRuntime


class AuditorAgent:
    name = "agent:auditor"

    def audit(self, runtime: "RIFRuntime") -> dict[str, Any]:
        """
        Combine the auditor identifier with the runtime audit summary.
        
        Parameters:
        	runtime (RIFRuntime): Runtime instance providing the audit summary.
        
        Returns:
        	dict[str, Any]: A dictionary containing the auditor identifier and audit summary values.
        """
        return {
            "agent": self.name,
            **runtime.audit_summary(),
        }
