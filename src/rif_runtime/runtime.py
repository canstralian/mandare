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
from .storage.jsonl import HashChainedJsonlStore, JsonlStore


class RIFRuntime:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        """
        Initialize the runtime with configuration, governance components, persistent stores, and the restored posture.
        
        Parameters:
        	data_dir (str | Path | None): Directory for persistent runtime state. When omitted, uses the configured data directory.
        """
        self.config = load_config()
        self.environment_name = self._configured_environment()
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
        # Hash-chained: the decision log is the audit trail, so a silently
        # edited row has to be detectable, not merely unlikely. Rows written
        # before chaining existed are reported as `unchained_leading` rather
        # than being counted as verified.
        self.decisions_store = HashChainedJsonlStore(self.decisions_path)
        self.posture_store = JsonlStore(self.data_dir / "posture_history.jsonl")
        self.metasploit = MetasploitGovernor()
        self.evidence_store = JsonlStore(self.data_dir / "metasploit_evidence.jsonl")
        # Re-entrant: evaluate() holds the lock across its call to
        # record_decision(), which acquires it again.
        self._lock = threading.RLock()
        self.posture = self._restore_posture()

    def _restore_posture(self) -> Posture:
        """
        Restore the runtime posture while enforcing the configured posture as a minimum floor.
        
        Returns:
            Posture: The posture restored from persisted state or decision history, raised to
            the configured posture when necessary.
        """
        return at_least_posture(self._restored_posture(), self._configured_posture())

    def _restored_posture(self) -> Posture:
        """
        Restore the latest valid persisted posture, or derive the posture by replaying recorded decisions.
        
        Returns:
            Posture: The restored or replayed posture.
        """
        for row in reversed(self.posture_store.read_all()):
            try:
                return Posture(row["new_posture"])
            except (KeyError, ValueError):
                continue
        return ReplayEngine(self.decisions_path).recover_posture()

    def _configured_posture(self) -> Posture:
        """Posture floor declared by configuration."""
        return Posture(get_settings().runtime.posture)

    def _configured_environment(self) -> str:
        """Determine the active environment from runtime configuration.
        
        Returns:
        	str: The configured environment, or the default environment when none is configured.
        
        Raises:
        	ValueError: If an explicitly configured environment is unknown.
        """
        configured = get_settings().runtime.environment
        if configured is None:
            return self.config.default_environment
        if configured in self.config.environments:
            return configured
        raise ValueError(
            f"configured environment {configured!r} is not defined in "
            f"environments.yaml (known: {sorted(self.config.environments)})"
        )

    @property
    def profile(self) -> EnvironmentProfile:
        """Provide the profile for the active environment.
        
        Returns:
            EnvironmentProfile: The profile associated with the active environment.
        """
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
        """Summarize recent denials and total recorded telemetry events.
        
        Returns:
            dict[str, Any]: A summary containing denial count from the previous 60 minutes and total event count.
        """
        return {
            "recent_denials_60m": self.reflexive.telemetry.denial_count(minutes=60),
            "event_count": len(self.reflexive.telemetry.events),
        }

    def persisted_summary(
        self, decisions: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        # One read feeds all three decision figures. Four separate reads of a
        # log being appended to concurrently can disagree, so the "summary"
        # would describe no single state of the file.
        """
        Summarize persisted governance decisions and posture transitions.
        
        Parameters:
            decisions (list[dict[str, Any]] | None): Optional decision snapshot to summarize; when omitted, reads the persisted decisions.
        
        Returns:
            dict[str, Any]: Counts of decisions, posture transitions, decisions grouped by result, and decisions grouped by matched rule.
        """
        rows = self.decisions_store.read_all() if decisions is None else decisions
        return {
            "decisions_total": self.decisions_store.count(rows),
            "posture_transitions_total": self.posture_store.count(),
            "decisions_by_result": self.decisions_store.count_by("decision", rows),
            "decisions_by_rule": self.decisions_store.count_by("matched_rule", rows),
        }

    def verify_decision_chain(
        self, decisions: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Recomputes the hash chain for persisted decisions and reports its integrity.
        
        Parameters:
            decisions (list[dict[str, Any]] | None): Optional decision records to verify
                instead of reading the persisted decision log.
        
        Returns:
            dict[str, Any]: Hash-chain integrity details for the supplied or persisted
                decision records.
        """
        return self.decisions_store.verify(decisions).as_dict()

    def audit_summary(self) -> dict[str, Any]:
        # GET /v1/audit previously re-read and re-hashed decisions.jsonl five
        # times per call, on a route that is unauthenticated unless
        # RIF_REQUIRE_READ_AUTH is set. Read once, derive everything from it.
        """
        Summarize the runtime's current governance state and persisted decision history.
        
        Returns:
            dict[str, Any]: A summary containing the active environment and posture,
            live graph and telemetry data, persisted decision statistics, and decision
            chain integrity results.
        """
        decisions = self.decisions_store.read_all()
        return {
            "environment": self.environment_name,
            "posture": self.posture.value
            if hasattr(self.posture, "value")
            else self.posture,
            "live": {
                "graph": self.graph_summary(),
                "telemetry": self.telemetry_summary(),
            },
            "persisted": self.persisted_summary(decisions),
            "decision_chain": self.verify_decision_chain(decisions),
        }
