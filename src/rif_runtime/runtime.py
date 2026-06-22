from hashlib import sha256
from uuid import uuid4

from .config import load_config
from .policy import PolicyEngine
from .schemas import GovernanceArtifact, PolicyRequest, Posture
from .governance.reflexive import ReflexiveLoop
from .graph.memory import GovernanceGraph
from .storage.jsonl import JsonlStore
from .model_layer import LocalModelError
from .model_router import ModelRouter


class RIFRuntime:
    def __init__(self):
        self.config = load_config()
        self.environment_name = self.config.default_environment
        self.posture = Posture.normal
        self.policy = PolicyEngine()
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
        decision = self.policy.evaluate(req, self.environment_name, self.profile, self.posture)
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

    def evaluate_with_models(self, req: PolicyRequest, request_text: str, router: ModelRouter | None = None) -> GovernanceArtifact:
        """Attach untrusted model advice without delegating authorization to a model."""
        router = router or ModelRouter()
        intent = None
        try:
            intent = router.classify(request_text)
        except LocalModelError:
            pass

        decision = self.evaluate(req)
        route = router.route(intent)
        reasoning = None
        if decision.decision.value == "allow" and route.uses_deep_reasoner:
            try:
                reasoning = router.reason(request_text, [decision.reason])
            except LocalModelError:
                pass

        summary = router.summarise(
            f"policy={decision.model_dump(mode='json')} intent={intent.model_dump() if intent else None} "
            f"reasoning={reasoning.model_dump() if reasoning else None}"
        )
        return GovernanceArtifact(
            request_id=str(uuid4()),
            input_hash=sha256(request_text.encode()).hexdigest(),
            intent=intent,
            policy_decision=decision,
            model_route=route,
            deep_reasoning=reasoning,
            final_summary=summary,
            replay_metadata={
                "runtime_version": "rif-runtime-v0.3",
                "environment": self.environment_name,
                "posture_after_decision": self.posture.value,
                "models": route.stages,
            },
        )

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
