"""Enterprise-grade governed agents for the RIF runtime.

Public API:
    BaseAgent          - Base class for building governed agents
    OrchestratorAgent  - Coordinates downstream actions with circuit breakers
    AuditorAgent       - Verifies audit chain integrity and detects anomalies
    DeputyAgent        - Reviews decisions and manages escalation workflows
    AgentManifest      - Declarative agent metadata

    CircuitBreaker     - Thread-safe circuit breaker
    CircuitBreakerConfig - Circuit breaker tuning
    CircuitOpen        - Exception for open circuits
    CircuitState       - Circuit state enum

    PolicyGate         - Pre-execution policy enforcement
    PolicyGateError    - Exception for policy denials
    GateResult         - Policy gate check outcome

    ActionResult       - Structured action dispatch result
"""

from .template import ActionResult, BaseAgent
from .orchestrator import OrchestratorAgent
from .auditor import AuditFinding, AuditReport, AuditorAgent
from .deputy import DeputyAgent, EscalationLevel, ReviewFinding
from .manifest import AgentManifest
from ._circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerStats,
    CircuitOpen,
    CircuitState,
)
from ._policy_gate import GateResult, PolicyGate, PolicyGateError

__all__ = [
    "ActionResult",
    "AgentManifest",
    "AuditFinding",
    "AuditReport",
    "AuditorAgent",
    "BaseAgent",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitOpen",
    "CircuitState",
    "DeputyAgent",
    "EscalationLevel",
    "GateResult",
    "OrchestratorAgent",
    "PolicyGate",
    "PolicyGateError",
    "ReviewFinding",
]
