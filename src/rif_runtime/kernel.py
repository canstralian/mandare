"""RIFKernel: the execution kernel pipeline.

    Intent -> Context -> Governance -> State -> Budget -> Capability Router
          -> Execution -> Evidence -> Telemetry -> Evolution

The agent is not the runtime. An execution engine is one capability the kernel
manages, invoked only after governance admits the intent, and only over the
capabilities the router selected.

Collaborators are constructor-injected and each defaults to a real
implementation, so `RIFKernel(engine)` works out of the box while tests can
substitute any stage.

Two properties are load-bearing:

* **Evidence is recorded on every path.** A denied intent is appended to the
  ledger *before* the safe response is returned. Recording only successes would
  drop exactly the events that drive posture escalation.
* **Denials reach the governance circuit.** Every decision — pre-flight,
  per-call, and budget — is committed through `RIFRuntime.record_decision`, so
  the reflexive loop, the graph, and the decision log stay in agreement with
  the HTTP control plane.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .budget import BudgetAccount, BudgetManager, BudgetSnapshot
from .capabilities import CapabilityRouter, RoutingResult
from .context import ContextAssembler, ExecutionContext
from .evidence import EvidenceLedger
from .evolution import EvolutionQueue, ProposalSource
from .execution import (
    CapabilityApprovalGate,
    ExecutionEngine,
    ExecutionResult,
)
from .governance.engine import GovernanceDecision, GovernanceEngine
from .identity import IdentityResolver, IdentityState
from .intent import Intent
from .state import RuntimeState
from .telemetry import Telemetry


class KernelResult(BaseModel):
    allowed: bool
    response: str
    intent: Intent
    identity: IdentityState
    decision: GovernanceDecision
    capabilities: list[str] = Field(default_factory=list)
    execution: ExecutionResult | None = None
    budget: BudgetSnapshot | None = None
    evidence_id: str | None = None
    evidence_hash: str | None = None
    telemetry: dict[str, Any] = Field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "intent_id": self.intent.intent_id,
            "principal": self.identity.principal,
            "decision": self.decision.summary(),
            "capabilities": self.capabilities,
            "evidence_hash": self.evidence_hash,
        }


class RIFKernel:
    def __init__(
        self,
        engine: ExecutionEngine,
        state: RuntimeState | None = None,
        identity: IdentityResolver | None = None,
        context: ContextAssembler | None = None,
        governance: GovernanceEngine | None = None,
        router: CapabilityRouter | None = None,
        ledger: EvidenceLedger | None = None,
        telemetry: Telemetry | None = None,
        budget: BudgetManager | None = None,
        evolution: EvolutionQueue | None = None,
    ) -> None:
        self.engine = engine
        self.state = state or RuntimeState()
        self.identity = identity or IdentityResolver()
        self.context = context or ContextAssembler()
        # Share the runtime's PolicyStore so kernel and HTTP control plane
        # evaluate against one rule set rather than two copies of the file.
        self.governance = governance or GovernanceEngine(
            policy_store=self.state.runtime.policy_store
        )
        self.router = router or CapabilityRouter(governance=self.governance)
        self.ledger = ledger or EvidenceLedger()
        self.telemetry = telemetry or Telemetry()
        self.budget = budget or BudgetManager()
        self.evolution = evolution or EvolutionQueue()

    async def run(
        self,
        user_request: str,
        actor: str = "agent:kernel",
        capability_limit: int | None = None,
        **metadata: str,
    ) -> KernelResult:
        self.telemetry.start()

        # 1-3. Intent, identity, context.
        intent = self.state.capture_intent(user_request, actor=actor, **metadata)
        identity = self.identity.resolve(intent)
        context = self.context.build(intent, identity, self.state)

        # 4. Governance (pre-flight). Admission only -- per-call mediation
        #    happens inside the gate during execution.
        decision = self.governance.evaluate(context)
        self._commit(decision)

        if not decision.allowed:
            return self._denied(intent, identity, context, decision)

        # 5-6. Budget, then capability routing within it.
        account = self.budget.open(intent, identity)
        routing = self.router.select(context, budget=account, limit=capability_limit)

        # 7. Execution, with every tool call mediated by the gate.
        gate = CapabilityApprovalGate(
            context, self.governance, ledger=self.ledger, budget=account
        )
        execution = await self._execute(context, routing, gate, account)

        # 8-10. Evidence, telemetry, evolution.
        return self._completed(
            intent, identity, context, decision, routing, execution, gate, account
        )

    async def _execute(
        self,
        context: ExecutionContext,
        routing: RoutingResult,
        gate: CapabilityApprovalGate,
        account: BudgetAccount,
    ) -> ExecutionResult:
        try:
            result = await self.engine.run(context, routing.selected, gate)
        except Exception as error:  # noqa: BLE001 - engine faults are data here
            # An engine fault is a governance-relevant outcome, not a crash to
            # propagate: it is recorded, queued for evolution, and reported.
            return ExecutionResult(
                success=False,
                error=f"{type(error).__name__}: {error}",
                model=getattr(self.engine, "model", None),
            )
        if result.latency_ms == 0.0:
            result = result.model_copy(
                update={"latency_ms": self.telemetry.elapsed_ms()}
            )
        return result

    def _denied(
        self,
        intent: Intent,
        identity: IdentityState,
        context: ExecutionContext,
        decision: GovernanceDecision,
    ) -> KernelResult:
        record = self.ledger.record(
            "intent.denied",
            context=context.summary(),
            decision=decision.summary(),
        )
        sample = self.telemetry.capture(
            success=False, error=decision.reason, intent_id=intent.intent_id
        )
        self.evolution.enqueue(
            ProposalSource.governance_denial,
            f"intent denied by {decision.matched_rule}",
            intent_id=intent.intent_id,
            matched_rule=decision.matched_rule,
            reason=decision.reason,
        )
        return KernelResult(
            allowed=False,
            response=decision.response or "",
            intent=intent,
            identity=identity,
            decision=decision,
            evidence_id=record.event_id,
            evidence_hash=record.current_hash,
            telemetry=sample.model_dump(mode="json"),
        )

    def _completed(
        self,
        intent: Intent,
        identity: IdentityState,
        context: ExecutionContext,
        decision: GovernanceDecision,
        routing: RoutingResult,
        execution: ExecutionResult,
        gate: CapabilityApprovalGate,
        account: BudgetAccount,
    ) -> KernelResult:
        try:
            account.consume(tokens=execution.tokens, seconds=self.telemetry.elapsed())
        except Exception:  # noqa: BLE001 - overspend is reported, not raised
            self.evolution.enqueue(
                ProposalSource.budget_exhausted,
                "execution exceeded its budget",
                intent_id=intent.intent_id,
                spent=account.spent(),
            )

        record = self.ledger.record(
            "execution.completed" if execution.success else "execution.failed",
            context=context.summary(),
            decision=decision.summary(),
            model=execution.model,
            capabilities=routing.summary(),
            approved_calls=[call.model_dump() for call in gate.approved],
            denied_calls=gate.denials,
            budget=BudgetSnapshot.of(account).model_dump(mode="json"),
            success=execution.success,
            error=execution.error,
        )

        # Per-call denials are governance events in their own right: commit
        # them so they count toward posture just like a denied HTTP request.
        for denial in gate.denials:
            self._commit_capability_denial(context, denial)

        if not execution.success:
            self.evolution.enqueue(
                ProposalSource.execution_failure,
                "execution engine failed",
                intent_id=intent.intent_id,
                error=execution.error,
            )
        for rejection in routing.rejected:
            self.evolution.enqueue(
                ProposalSource.capability_gap,
                f"capability {rejection.capability} unavailable: {rejection.reason}",
                intent_id=intent.intent_id,
            )

        sample = self.telemetry.capture(
            tokens=execution.tokens,
            latency_ms=execution.latency_ms,
            capability_calls=len(execution.capability_calls),
            success=execution.success,
            error=execution.error,
            intent_id=intent.intent_id,
        )
        return KernelResult(
            allowed=True,
            response=execution.output,
            intent=intent,
            identity=identity,
            decision=decision,
            capabilities=routing.names(),
            execution=execution,
            budget=BudgetSnapshot.of(account),
            evidence_id=record.event_id,
            evidence_hash=record.current_hash,
            telemetry=sample.model_dump(mode="json"),
        )

    def _commit(self, decision: GovernanceDecision) -> None:
        """Feed a decision through the runtime's governance circuit."""

        self.state.runtime.record_decision(decision.policy_decision)

    def _commit_capability_denial(
        self, context: ExecutionContext, denial: dict[str, Any]
    ) -> None:
        from .schemas import Decision, PolicyDecision

        self.state.runtime.record_decision(
            PolicyDecision(
                decision=Decision.deny,
                actor=context.intent.actor,
                action=f"capability.{denial['capability']}",
                target=str(denial["target"]),
                environment=context.environment,
                posture=self.state.posture,
                reason=str(denial["reason"]),
                matched_rule=str(denial["matched_rule"]),
            )
        )

    def summary(self) -> dict[str, Any]:
        return {
            "environment": self.state.environment_name,
            "posture": self.state.posture.value,
            "mode": self.state.mode.value,
            "policy_version": self.governance.policy_version(),
            "evidence": self.ledger.summary(),
            "telemetry": self.telemetry.summary(),
            "evolution": self.evolution.summary(),
        }
