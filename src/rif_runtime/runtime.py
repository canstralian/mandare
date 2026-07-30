from __future__ import annotations

import threading
from typing import Any

from .config import load_config
from .policy import PolicyEngine
from .schemas import EnvironmentProfile, PolicyDecision, PolicyRequest, Posture
from .governance.reflexive import ReflexiveLoop
from .governance.posture import escalate_posture
from .graph.memory import GovernanceGraph
from .paths import DECISIONS_FILE, EVIDENCE_FILE, POSTURE_HISTORY_FILE, data_path
from .replay import ReplayEngine
from .storage.jsonl import JsonlStore
from .configuration.policies import PolicyStore
from .mcp.metasploit import (
    CapabilityToken,
    GovernanceMode,
    GovernanceOutcome,
    MetasploitGovernor,
    MetasploitIntent,
)


class RIFRuntime:
    def __init__(self) -> None:
        self.config = load_config()
        self.environment_name = self.config.default_environment
        self.posture = Posture.normal
        self.policy = PolicyEngine()
        self.policy_store = PolicyStore()
        self.reflexive = ReflexiveLoop()
        self.governance_graph = GovernanceGraph()
        # Paths resolve here, not at import, so RIF_DATA_DIR set before
        # construction takes effect.
        self.decisions_store = JsonlStore(data_path(DECISIONS_FILE))
        self.posture_store = JsonlStore(data_path(POSTURE_HISTORY_FILE))
        self.metasploit = MetasploitGovernor()
        self.evidence_store = JsonlStore(data_path(EVIDENCE_FILE))
        # Re-entrant: the API shares one RIFRuntime across FastAPI's sync
        # threadpool, and the guarded paths below nest (evaluate ->
        # record_decision -> _commit).
        self._lock = threading.RLock()

    @property
    def profile(self) -> EnvironmentProfile:
        return self.config.environments[self.environment_name]

    def set_environment(self, name: str) -> None:
        if name not in self.config.environments:
            raise ValueError(f"unknown environment: {name}")
        self.environment_name = name

    def evaluate(self, req: PolicyRequest, record: bool = True) -> PolicyDecision:
        # Evaluate and commit under one lock (re-entrant, so record_decision
        # can re-acquire): the posture the decision is stamped with must be the
        # posture it is committed against, or a concurrent escalation between
        # the two could persist a decision attributed to a stale rung.
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
        with self._lock:
            self._commit(decision)
        return decision

    def _commit(self, decision: PolicyDecision, *, severe: bool = False) -> None:
        """Record one decision and its posture transition. Caller holds the lock.

        The single write path for the governance circuit: graph edge, reflexive
        posture update, decision append, and posture-transition append. Both
        `record_decision` and `evaluate_metasploit` go through it so the two
        cannot drift in what they persist.
        """
        self.governance_graph.record_decision(decision)
        old_posture = self.posture
        self.posture = self.reflexive.observe(decision, self.posture)
        if severe:
            self.posture = escalate_posture(self.posture)

        self.decisions_store.append(decision.model_dump())

        if old_posture != self.posture:
            # .value, not str(): a `str, Enum` stringifies as "Posture.normal",
            # which would not match the plain "normal" that pydantic writes
            # into decisions.jsonl.
            self.posture_store.append(
                {
                    "old_posture": old_posture.value,
                    "new_posture": self.posture.value,
                }
            )

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
            self._commit(outcome.decision, severe=outcome.severe)
            self.evidence_store.append(outcome.evidence.model_dump())
            return outcome

    def graph_summary(self) -> dict[str, int]:
        return self.governance_graph.summary()

    def telemetry_summary(self) -> dict[str, int]:
        return {
            "recent_denials_60m": self.reflexive.telemetry.denial_count(minutes=60),
            "event_count": len(self.reflexive.telemetry.events),
        }

    def persisted_summary(self) -> dict[str, Any]:
        # One pass over decisions.jsonl for both tallies; the log is append-only
        # and unbounded, so each extra read costs a full file scan.
        tallies = self.decisions_store.summarise("decision", "matched_rule")
        return {
            "decisions_total": sum(tallies["decision"].values()),
            "posture_transitions_total": self.posture_store.count(),
            "decisions_by_result": tallies["decision"],
            "decisions_by_rule": tallies["matched_rule"],
        }

    def recovered_summary(self) -> dict[str, Any]:
        """Rebuild graph and posture from the persisted decision log.

        Forensic view for `GET /v1/recovered-state`: what a cold start would
        reconstruct from `decisions.jsonl` alone, independent of this process's
        in-memory state.
        """
        return ReplayEngine(str(self.decisions_store.path)).recover().as_dict()

    def audit_summary(self) -> dict[str, Any]:
        return {
            "environment": self.environment_name,
            "posture": self.posture.value,
            "live": {
                "graph": self.graph_summary(),
                "telemetry": self.telemetry_summary(),
            },
            "persisted": self.persisted_summary(),
        }
