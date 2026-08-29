from __future__ import annotations

from collections.abc import Iterable

from rif_runtime.execution.exceptions import (
    CapabilityNotFoundError,
    PolicyViolationError,
)

from .capability import Capability
from .models import (
    AgentIdentity,
    BehaviorEvidence,
    CapabilityDeclaration,
    CapabilityEvaluation,
    CapabilityRecord,
    CapabilityStatus,
)
from .trust import CapabilityTrustEngine, TrustDecision


class CapabilityRegistry:
    """Registry of executable capabilities and their governance records.

    Registration is separate from authority. A capability can be discovered,
    inspected and evaluated without becoming executable. Identity, declared
    authority and observed behaviour are carried with the governance record.
    """

    def __init__(
        self,
        capabilities: Iterable[Capability] | None = None,
        trust_engine: CapabilityTrustEngine | None = None,
    ) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._records: dict[str, CapabilityRecord] = {}
        self._trust_engine = trust_engine or CapabilityTrustEngine()

        if capabilities is not None:
            for capability in capabilities:
                self.register(capability)

    def register(
        self,
        capability: Capability,
        record: CapabilityRecord | None = None,
    ) -> None:
        if capability.name in self._capabilities:
            raise ValueError(f"Capability already registered: {capability.name}")
        if record is not None and record.id != capability.name:
            raise ValueError(
                "Capability record id must match executable capability name"
            )
        self._capabilities[capability.name] = capability
        if record is not None:
            self._records[capability.name] = record

    def register_record(self, record: CapabilityRecord) -> None:
        """Register governance metadata before an executable adapter exists."""
        if record.id in self._records:
            raise ValueError(f"Capability record already registered: {record.id}")
        self._records[record.id] = record

    def bind_identity(self, name: str, identity: AgentIdentity) -> CapabilityRecord:
        record = self.record(name)
        record.identity = identity
        return record

    def declare(self, name: str, declaration: CapabilityDeclaration) -> CapabilityRecord:
        record = self.record(name)
        record.declaration = declaration
        return record

    def resolve(self, name: str) -> Capability:
        try:
            return self._capabilities[name]
        except KeyError as exc:
            raise CapabilityNotFoundError(f"Unknown capability: {name}") from exc

    def record(self, name: str) -> CapabilityRecord:
        try:
            return self._records[name]
        except KeyError as exc:
            raise CapabilityNotFoundError(
                f"No governance record for capability: {name}"
            ) from exc

    def admit(self, name: str) -> CapabilityRecord:
        """Admit only after integrity, evaluation, identity and declaration pass."""
        record = self.record(name)
        if not record.integrity.verified:
            raise PolicyViolationError(
                f"Capability admission denied: integrity not verified: {name}"
            )
        if not any(evaluation.passed for evaluation in record.evaluations):
            raise PolicyViolationError(
                f"Capability admission denied: no passing evaluation: {name}"
            )
        if record.identity is None:
            raise PolicyViolationError(
                f"Capability admission denied: agent identity missing: {name}"
            )
        if record.declaration is None:
            raise PolicyViolationError(
                f"Capability admission denied: declaration missing: {name}"
            )
        if name not in record.identity.declared_capabilities:
            raise PolicyViolationError(
                f"Capability admission denied: identity does not declare {name}"
            )
        record.lifecycle.status = CapabilityStatus.admitted
        return record

    def add_evaluation(self, name: str, evaluation: CapabilityEvaluation) -> None:
        record = self.record(name)
        record.evaluations.append(evaluation)
        if evaluation.passed:
            record.lifecycle.status = CapabilityStatus.evaluated

    def observe(self, name: str, evidence: BehaviorEvidence) -> CapabilityRecord:
        """Record behaviour and immediately recompute execution trust."""
        record = self.record(name)
        record.behavior_evidence.append(evidence)
        self._trust_engine.assess(record)
        return record

    def assess_trust(self, name: str):
        """Recompute trust from the complete observed evidence stream."""
        return self._trust_engine.assess(self.record(name))

    def authorize(
        self,
        name: str,
        *,
        action: str,
        target: str | None = None,
    ) -> TrustDecision:
        """Enforce declared authority and current behavioural trust."""
        record = self.record(name)
        decision = self._trust_engine.authorize(
            record,
            action=action,
            target=target,
        )
        if decision is TrustDecision.deny:
            raise PolicyViolationError(
                f"Capability authorization denied: {name}:{action}"
            )
        if decision is TrustDecision.quarantine:
            raise PolicyViolationError(
                f"Capability quarantined by trust policy: {name}:{action}"
            )
        return decision

    def __contains__(self, name: object) -> bool:
        return name in self._capabilities

    def __len__(self) -> int:
        return len(self._capabilities)
