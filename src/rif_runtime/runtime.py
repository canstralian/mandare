import threading
from typing import Any

from .config import load_config
from .configuration.policies import PolicyStore
from .evidence import EvidenceLedger
from .governance.posture import escalate_posture
from .governance.reflexive import ReflexiveLoop
from .graph.memory import GovernanceGraph
from .mcp.metasploit import (
    CapabilityToken,
    GovernanceMode,
    GovernanceOutcome,
    MetasploitGovernor,
    MetasploitIntent,
)
from .policy import PolicyEngine
from .schemas import EnvironmentProfile, PolicyDecision, PolicyRequest, Posture
from .storage.jsonl import JsonlStore


class RIFRuntime:
    def __init__(self) -> None:
        self.config = load_config()
        self.environment_name = self.config.default_environment
        self.posture = Posture.normal
        self.policy = PolicyEngine()
        self.policy_store = PolicyStore()
        self.reflexive = ReflexiveLoop()
        self.governance_graph = GovernanceGraph()
        # EvidenceLedger owns the decisions.jsonl store and adds the v1
        # causal envelope on every append. decisions_store remains the
        # underlying JsonlStore for count/summary helpers.
        self.evidence_ledger = EvidenceLedger("data/decisions.jsonl")
        self.decisions_store = self.evidence_ledger.store
        self.posture_store = JsonlStore("data/posture_history.jsonl")
        self.metasploit = MetasploitGovernor()
        self.evidence_store = JsonlStore("data/metasploit_evidence.jsonl")
        self._lock = threading.Lock()

    @property
    def profile(self) -> EnvironmentProfile:
        return self.config.environments[self.environment_name]

    def set_environment(self, name: str) -> None:
        if name not in self.config.environments:
            raise ValueError(f"unknown environment: {name}")
        self.environment_name = name

    def evaluate(self, req: PolicyRequest, record: bool = True) -> PolicyDecision:
        # record=False is a side-effect-free dry run: return the computed
        # decision without mutating posture or appending to the JSONL stores.
        # The unauthenticated simulation routes (e.g. /v1/mcp/invoke) use it so
        # they cannot drive posture escalation or flood the audit log.
        if not record:
            return self.policy.evaluate(
                req,
                self.environment_name,
                self.profile,
                self.posture,
                self.policy_store.list(),
            )
        # Hold the lock across evaluate+record so the posture stamped on the
        # decision matches the posture RMW that follows (no TOCTOU under the
        # FastAPI sync threadpool).
        with self._lock:
            decision = self.policy.evaluate(
                req,
                self.environment_name,
                self.profile,
                self.posture,
                self.policy_store.list(),
            )
            return self._record_decision_unlocked(decision)

    def record_decision(self, decision: PolicyDecision) -> PolicyDecision:
        """Feed an already-computed decision through the governance circuit.

        Used by `evaluate()` for policy-gated requests, and directly by
        callers (e.g. eval harnesses) that need to record a governance-relevant
        outcome — such as a verification failure — that wasn't produced by
        `PolicyEngine.evaluate()` itself but should still drive posture
        escalation and land in the audit trail.
        """
        # Same lock as evaluate_metasploit: FastAPI's sync threadpool can run
        # concurrent evaluates against one RIFRuntime, and posture RMW + JSONL
        # appends must not interleave.
        with self._lock:
            return self._record_decision_unlocked(decision)

    def _record_decision_unlocked(self, decision: PolicyDecision) -> PolicyDecision:
        self.governance_graph.record_decision(decision)
        old_posture = self.posture
        self.posture = self.reflexive.observe(decision, self.posture)

        # Evidence ledger appends a v1 causal envelope (schema_version,
        # sequence, previous_hash, record_hash) around the JSON-native
        # decision payload. Legacy rows without the envelope stay readable.
        self.evidence_ledger.append_decision(decision)

        if old_posture != self.posture:
            self.posture_store.append(
                {
                    "old_posture": str(old_posture),
                    "new_posture": str(self.posture),
                }
            )
        return decision

    def reset_posture(self) -> Posture:
        """Return to ``normal`` and clear denial pressure so reset sticks."""

        with self._lock:
            self.posture = Posture.normal
            self.reflexive.telemetry.clear()
            return self.posture

    def evaluate_metasploit(
        self,
        intent: MetasploitIntent,
        mode: GovernanceMode = GovernanceMode.read_only_firewall,
        token: CapabilityToken | None = None,
        record: bool = True,
    ) -> GovernanceOutcome:
        # Serialise the read-modify-write of posture and the JSONL appends:
        # the API shares one RIFRuntime across FastAPI's sync threadpool.
        with self._lock:
            outcome = self.metasploit.evaluate(
                intent,
                mode=mode,
                env_name=self.environment_name,
                posture=self.posture,
                token=token,
            )
            # record=False is a side-effect-free dry run (see evaluate()): the
            # unauthenticated /v1/mcp/metasploit/evaluate route uses it so
            # simulation cannot escalate posture or write to the stores.
            if not record:
                return outcome
            decision = outcome.decision
            self.governance_graph.record_decision(decision)
            old_posture = self.posture
            self.posture = self.reflexive.observe(decision, self.posture)
            if outcome.severe:
                self.posture = escalate_posture(self.posture)

            self.evidence_ledger.append_decision(decision)
            self.evidence_store.append(outcome.evidence.model_dump(mode="json"))

            if old_posture != self.posture:
                self.posture_store.append(
                    {
                        "old_posture": str(old_posture),
                        "new_posture": str(self.posture),
                    }
                )
            return outcome

    def graph_summary(self) -> dict[str, Any]:
        return self.governance_graph.summary()

    def telemetry_summary(self) -> dict[str, Any]:
        return {
            "recent_denials_60m": self.reflexive.telemetry.denial_count(minutes=60),
            "event_count": len(self.reflexive.telemetry.events),
        }

    def persisted_summary(self) -> dict[str, Any]:
        return {
            "decisions_total": self.decisions_store.count(),
            "posture_transitions_total": self.posture_store.count(),
            "decisions_by_result": self.decisions_store.count_by("decision"),
            "decisions_by_rule": self.decisions_store.count_by("matched_rule"),
        }

    def audit_summary(self) -> dict[str, Any]:
        return {
            "environment": self.environment_name,
            "posture": self.posture.value
            if hasattr(self.posture, "value")
            else self.posture,
            "live": {
                "graph": self.graph_summary(),
                "telemetry": self.telemetry_summary(),
            },
            "persisted": self.persisted_summary(),
        }
