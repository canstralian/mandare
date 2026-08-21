import threading
from pathlib import Path
from typing import Any

from .config import get_settings, load_config
from .configuration.policies import PolicyStore
from .governance.posture import at_least_posture, escalate_posture
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
from .replay import ReplayEngine
from .schemas import EnvironmentProfile, PolicyDecision, PolicyRequest, Posture
from .storage.jsonl import JsonlStore


class RIFRuntime:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.config = load_config()
        self.environment_name = self.config.default_environment
        # One configured directory owns every piece of persistent state —
        # policies, decisions, posture history, evidence — so RIF_DATA_DIR
        # (equivalently [paths] data_dir in rif.toml) relocates all of them
        # together. Tests pass an explicit tmp_path instead.
        self.data_dir = Path(
            data_dir if data_dir is not None else get_settings().paths.data_dir
        )
        self.policy = PolicyEngine()
        self.policy_store = PolicyStore(self.data_dir / "policies.json")
        self.reflexive = ReflexiveLoop()
        self.governance_graph = GovernanceGraph()
        self.decisions_path = self.data_dir / "decisions.jsonl"
        self.decisions_store = JsonlStore(self.decisions_path)
        self.posture_store = JsonlStore(self.data_dir / "posture_history.jsonl")
        self.metasploit = MetasploitGovernor()
        self.evidence_store = JsonlStore(self.data_dir / "metasploit_evidence.jsonl")
        # Re-entrant: evaluate() holds the lock across its call to
        # record_decision(), which acquires it again.
        self._lock = threading.RLock()
        self.posture = self._restore_posture()

    def _restore_posture(self) -> Posture:
        """Derive the posture this process must start in.

        ``posture_history.jsonl`` is authoritative when it has rows: it records
        every transition, including an operator's explicit set or reset, so its
        last entry is the posture the runtime was left in. Falling back to
        replaying ``decisions.jsonl`` covers a first boot after decisions were
        recorded without any transition (no escalation yet, hence ``normal``
        unless the denial thresholds say otherwise).

        Without this a restart silently dropped a ``locked`` runtime back to
        ``normal``, re-opening everything ``PolicyEngine.evaluate()``'s
        ``posture.locked`` check had shut down.

        The configured posture (``RIF_POSTURE`` / ``[runtime] posture``) is
        then applied as a *floor*, not an assignment. It was previously parsed,
        validated, and never read, so ``RIF_POSTURE=locked`` started a runtime
        that allowed everything. A floor is the safe reading of that setting:
        an operator who configures ``locked`` cannot have it quietly lowered by
        a stale ``normal`` in the history, while a runtime that escalated to
        ``restricted`` at runtime does not get relaxed back down to a
        configured ``normal`` either.
        """
        return at_least_posture(self._restored_posture(), self._configured_posture())

    def _restored_posture(self) -> Posture:
        """Last persisted posture, or the one replay derives from decisions."""
        for row in reversed(self.posture_store.read_all()):
            try:
                return Posture(row["new_posture"])
            except (KeyError, ValueError):
                continue
        return ReplayEngine(self.decisions_path).recover_posture()

    def _configured_posture(self) -> Posture:
        """Posture floor declared by configuration."""
        return Posture(get_settings().runtime.posture)

    @property
    def profile(self) -> EnvironmentProfile:
        return self.config.environments[self.environment_name]

    def set_posture(self, posture: Posture) -> Posture:
        """Set the posture explicitly, persisting the transition.

        Operator overrides land in the same log as reflexive escalations so
        `_restore_posture()` sees them after a restart — otherwise a reset
        would be undone by the next process start.
        """
        with self._lock:
            old_posture = self.posture
            self.posture = posture
            if old_posture != posture:
                self.posture_store.append(
                    {"old_posture": str(old_posture), "new_posture": str(posture)}
                )
            return self.posture

    def set_environment(self, name: str) -> None:
        if name not in self.config.environments:
            raise ValueError(f"unknown environment: {name}")
        self.environment_name = name

    def evaluate(self, req: PolicyRequest, record: bool = True) -> PolicyDecision:
        # Serialise the whole read-decide-write: the API shares one RIFRuntime
        # across FastAPI's sync threadpool, so evaluating outside the lock
        # could decide against a posture another thread has already escalated,
        # or overwrite that thread's transition on write-back.
        with self._lock:
            decision = self.policy.evaluate(
                req,
                self.environment_name,
                self.profile,
                self.posture,
                self.policy_store.list(),
            )
            # record=False is a side-effect-free dry run: return the computed
            # decision without mutating posture or appending to the JSONL
            # stores. The unauthenticated simulation routes (e.g.
            # /v1/mcp/invoke) use it so they cannot drive posture escalation or
            # flood the audit log.
            if not record:
                return decision
            return self.record_decision(decision)

    def record_decision(self, decision: PolicyDecision) -> PolicyDecision:
        """Feed an already-computed decision through the governance circuit.

        Used by `evaluate()` for policy-gated requests, and directly by
        callers (e.g. eval harnesses) that need to record a governance-relevant
        outcome — such as a verification failure — that wasn't produced by
        `PolicyEngine.evaluate()` itself but should still drive posture
        escalation and land in the audit trail.
        """
        # Same serialisation as evaluate() — direct callers get it too, and the
        # lock is re-entrant so evaluate() can hold it across this call.
        with self._lock:
            self.governance_graph.record_decision(decision)
            old_posture = self.posture
            self.posture = self.reflexive.observe(decision, self.posture)

            self.decisions_store.append(decision.model_dump())

            if old_posture != self.posture:
                self.posture_store.append(
                    {"old_posture": str(old_posture), "new_posture": str(self.posture)}
                )
            return decision

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

            self.decisions_store.append(decision.model_dump())
            self.evidence_store.append(outcome.evidence.model_dump())

            if old_posture != self.posture:
                self.posture_store.append(
                    {"old_posture": str(old_posture), "new_posture": str(self.posture)}
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
