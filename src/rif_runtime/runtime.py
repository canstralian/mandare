from .config import load_config
from .policy import PolicyEngine
from .schemas import PolicyRequest, Posture
from .governance.reflexive import ReflexiveLoop
from .graph.memory import GovernanceGraph
from .storage.jsonl import JsonlStore
from .configuration.policies import PolicyStore

class RIFRuntime:
    def __init__(self):
        self.config = load_config()
        self.environment_name = self.config.default_environment
        self.posture = Posture.normal
        self.policy = PolicyEngine()
        self.policy_store = PolicyStore()
        self.reflexive = ReflexiveLoop()
        self.governance_graph = GovernanceGraph()
        self.decisions_store = JsonlStore("data/decisions.jsonl")
        self.posture_store = JsonlStore("data/posture_history.jsonl")

    @property
    def profile(self):
        return self.config.environments[self.environment_name]

    def set_environment(self, name):
        if name not in self.config.environments:
            raise ValueError(f"unknown environment: {name}")
        self.environment_name = name

    def evaluate(self, req: PolicyRequest):
        decision = self.policy.evaluate(req, self.environment_name, self.profile, self.posture, self.policy_store.list())
        self.governance_graph.record_decision(decision)
        old_posture = self.posture
        self.posture = self.reflexive.observe(decision, self.posture)

        self.decisions_store.append(decision.model_dump())

        if old_posture != self.posture:
            self.posture_store.append({
                "old_posture": str(old_posture),
                "new_posture": str(self.posture)
            })
        return decision

    def graph_summary(self):
        return self.governance_graph.summary()

    def telemetry_summary(self):
        return {
            "recent_denials_60m": self.reflexive.telemetry.denial_count(minutes=60),
            "event_count": len(self.reflexive.telemetry.events),
        }


    def persisted_summary(self):
        return {
            "decisions_total": self.decisions_store.count(),
            "posture_transitions_total": self.posture_store.count(),
            "decisions_by_result": self.decisions_store.count_by("decision"),
            "decisions_by_rule": self.decisions_store.count_by("matched_rule"),
        }

    def audit_summary(self):
        return {
            "environment": self.environment_name,
            "posture": self.posture.value if hasattr(self.posture, "value") else self.posture,
            "live": {
                "graph": self.graph_summary(),
                "telemetry": self.telemetry_summary(),
            },
            "persisted": self.persisted_summary(),
        }
