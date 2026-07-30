from typing import Any

from fastapi import FastAPI, HTTPException

from . import __version__
from .auth import ControlPlaneAuth
from .runtime import RIFRuntime
from .schemas import McpInvokeRequest, PolicyDecision, PolicyRequest, Posture
from rif_runtime.agents.auditor import AuditorAgent
from rif_runtime.configuration.policies import PolicyRule
from rif_runtime.mcp.capabilities import capability_catalog
from rif_runtime.mcp.metasploit import CapabilityToken
from rif_runtime.mcp.requests import (
    MetasploitEvaluateRequest,
    MetasploitTokenRequest,
)

runtime = RIFRuntime()
app = FastAPI(title="RIF Runtime", version=__version__)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "environment": runtime.environment_name,
        "posture": runtime.posture,
    }


@app.get("/v1/environments")
def environments() -> dict[str, Any]:
    return {
        "current": runtime.environment_name,
        "environments": runtime.config.environments,
    }


@app.post("/v1/environment/{name}", dependencies=[ControlPlaneAuth])
def set_environment(name: str) -> dict[str, str]:
    try:
        runtime.set_environment(name)
        return {"current": runtime.environment_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/v1/policy/evaluate", dependencies=[ControlPlaneAuth])
def evaluate(req: PolicyRequest) -> PolicyDecision:
    return runtime.evaluate(req)


@app.post("/v1/posture/reset", dependencies=[ControlPlaneAuth])
def reset_posture() -> dict[str, str]:
    # Must be registered before /v1/posture/{posture}, otherwise "reset" is
    # captured as a Posture path param and FastAPI returns 422.
    runtime.posture = Posture.normal
    return {"posture": runtime.posture.value}


@app.post("/v1/posture/{posture}", dependencies=[ControlPlaneAuth])
def posture(posture: Posture) -> dict[str, str]:
    runtime.posture = posture
    return {"posture": runtime.posture.value}


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "RIF Runtime",
        "version": __version__,
        "status": "online",
        "routes": ["/health", "/docs", "/v1/environments", "/v1/policy/evaluate"],
    }


@app.get("/v1/graph/summary")
def graph_summary() -> dict[str, int]:
    return runtime.graph_summary()


@app.get("/v1/telemetry/summary")
def telemetry_summary() -> dict[str, int]:
    return runtime.telemetry_summary()


@app.get("/v1/audit")
def audit() -> dict[str, Any]:
    return AuditorAgent().audit(runtime)


@app.post("/v1/mcp/invoke")
def mcp_invoke(payload: McpInvokeRequest) -> PolicyDecision:
    # Unauthenticated simulation route: dry-run so it cannot mutate posture or
    # write to the decision log. The authenticated /v1/policy/evaluate is the
    # recording path. See runtime.evaluate(record=...).
    return runtime.evaluate(payload.to_policy_request(), record=False)


@app.get("/v1/mcp/metasploit/capabilities")
def metasploit_capabilities() -> dict[str, Any]:
    return capability_catalog()


@app.post("/v1/mcp/metasploit/evaluate")
def metasploit_evaluate(payload: MetasploitEvaluateRequest) -> dict[str, Any]:
    # Unauthenticated simulation route: dry-run so it cannot mutate posture or
    # write to the stores. Minting a capability token (the actual authorization)
    # goes through the guarded /v1/mcp/metasploit/token.
    outcome = runtime.evaluate_metasploit(
        payload.intent,
        mode=payload.mode,
        token=payload.token,
        record=False,
    )
    return {
        "decision": outcome.decision,
        "evidence": outcome.evidence,
        "simulated": outcome.simulated,
        "severe": outcome.severe,
        "posture": runtime.posture,
    }


@app.post("/v1/mcp/metasploit/token", dependencies=[ControlPlaneAuth])
def metasploit_token(payload: MetasploitTokenRequest) -> CapabilityToken:
    return runtime.metasploit.mint_token(
        payload.intent,
        approver=payload.approver,
        ttl_seconds=payload.ttl_seconds,
    )


@app.get("/v1/persistence/summary")
def persistence_summary() -> dict[str, Any]:
    return runtime.persisted_summary()


@app.get("/v1/recovered-state")
def recovered_state() -> dict[str, Any]:
    return runtime.recovered_summary()


@app.get("/v1/policies")
def list_policies() -> dict[str, Any]:
    return {"rules": [rule.model_dump() for rule in runtime.policy_store.list()]}


@app.put("/v1/policies/{rule_id}", dependencies=[ControlPlaneAuth])
def upsert_policy(rule_id: str, rule: PolicyRule) -> PolicyRule:
    if rule.id != rule_id:
        rule = rule.model_copy(update={"id": rule_id})
    return runtime.policy_store.upsert(rule)


@app.delete("/v1/policies/{rule_id}", dependencies=[ControlPlaneAuth])
def delete_policy(rule_id: str) -> dict[str, bool]:
    return {"deleted": runtime.policy_store.delete(rule_id)}
