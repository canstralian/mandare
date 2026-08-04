from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from rif_runtime.agents.auditor import AuditorAgent
from rif_runtime.configuration.policies import PolicyRule
from rif_runtime.mcp.capabilities import capability_catalog
from rif_runtime.mcp.metasploit import (
    CapabilityToken,
    GovernanceMode,
    MetasploitIntent,
)

from .auth import ControlPlaneAuth
from .replay import ReplayEngine
from .runtime import RIFRuntime
from .schemas import PolicyDecision, PolicyRequest, Posture

runtime = RIFRuntime()
app = FastAPI(title="RIF Runtime", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    """
    Report the current service health status, active environment, and posture.
    
    Returns:
        A dictionary containing the service status, active environment name, and current posture.
    """
    return {
        "status": "ok",
        "environment": runtime.environment_name,
        "posture": runtime.posture,
    }


@app.get("/v1/environments")
def environments() -> dict[str, Any]:
    """Return the current environment and the configured environments."""
    return {
        "current": runtime.environment_name,
        "environments": runtime.config.environments,
    }


@app.post("/v1/environment/{name}", dependencies=[ControlPlaneAuth])
def set_environment(name: str) -> dict[str, Any]:
    """
    Set the active runtime environment.
    
    Parameters:
    	name (str): Name of the environment to activate.
    
    Returns:
    	dict[str, Any]: The name of the active environment.
    """
    try:
        runtime.set_environment(name)
        return {"current": runtime.environment_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/v1/policy/evaluate", dependencies=[ControlPlaneAuth])
def evaluate(req: PolicyRequest) -> PolicyDecision:
    """Evaluate a policy request using the runtime.
    
    Parameters:
    	req (PolicyRequest): The policy request to evaluate.
    
    Returns:
    	PolicyDecision: The resulting policy decision.
    """
    return runtime.evaluate(req)


@app.post("/v1/posture/reset", dependencies=[ControlPlaneAuth])
def reset_posture() -> dict[str, Any]:
    # Must be registered before /v1/posture/{posture}, otherwise "reset" is
    # captured as a Posture path param and FastAPI returns 422.
    """
    Restore the runtime to its normal posture.
    
    Returns:
    	dict[str, Any]: A mapping containing the current posture value.
    """
    runtime.posture = Posture.normal
    return {"posture": runtime.posture.value}


@app.post("/v1/posture/{posture}", dependencies=[ControlPlaneAuth])
def posture(posture: Posture) -> dict[str, Any]:
    """Set the runtime posture.
    
    Parameters:
    	posture (Posture): The posture to apply to the runtime.
    
    Returns:
    	dict[str, Any]: The applied runtime posture.
    """
    runtime.posture = posture
    return {"posture": runtime.posture}


@app.get("/")
def root() -> dict[str, Any]:
    """
    Return service metadata and links to selected API routes.
    
    Returns:
        dict[str, Any]: A mapping containing the service name, online status, and route links.
    """
    return {
        "name": "RIF Runtime",
        "status": "online",
        "routes": ["/health", "/docs", "/v1/environments", "/v1/policy/evaluate"],
    }


@app.get("/v1/graph/summary")
def graph_summary() -> dict[str, Any]:
    """Return a summary of the runtime graph.
    
    Returns:
        dict[str, Any]: The runtime graph summary.
    """
    return runtime.graph_summary()


@app.get("/v1/telemetry/summary")
def telemetry_summary() -> dict[str, Any]:
    """Return a summary of runtime telemetry data.
    
    Returns:
    	dict[str, Any]: The current telemetry summary.
    """
    return runtime.telemetry_summary()


@app.get("/v1/audit")
def audit() -> dict[str, Any]:
    """Run an audit of the current runtime state.
    
    Returns:
    	dict[str, Any]: The audit results.
    """
    return AuditorAgent().audit(runtime)


@app.post("/v1/mcp/invoke")
def mcp_invoke(payload: dict[str, Any]) -> PolicyDecision:
    """
    Evaluate an MCP invocation as a non-recording policy decision.
    
    Parameters:
    	payload (dict[str, Any]): MCP invocation fields, including optional actor, target, and reason values.
    
    Returns:
    	PolicyDecision: The policy decision for the MCP invocation.
    """
    from rif_runtime.schemas import PolicyRequest

    req = PolicyRequest(
        actor=payload.get("actor", "agent:mcp"),
        action="mcp.invoke",
        target=payload.get("target", "unknown"),
        reason=payload.get("reason"),
    )
    # Unauthenticated simulation route: dry-run so it cannot mutate posture or
    # write to the decision log. The authenticated /v1/policy/evaluate is the
    # recording path. See runtime.evaluate(record=...).
    return runtime.evaluate(req, record=False)


@app.get("/v1/mcp/metasploit/capabilities")
def metasploit_capabilities() -> dict[str, Any]:
    """Return the available Metasploit capability catalog."""
    return capability_catalog()


@app.post("/v1/mcp/metasploit/evaluate")
def metasploit_evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate a Metasploit intent in a non-recording simulation.
    
    Parameters:
        payload (dict[str, Any]): Request data containing the Metasploit intent,
            governance mode, and optional capability token.
    
    Returns:
        dict[str, Any]: Evaluation decision, evidence, simulation and severity
            indicators, and the current posture.
    
    Raises:
        HTTPException: If the intent, governance mode, or capability token is
            invalid.
    """
    try:
        intent = MetasploitIntent.model_validate(payload.get("intent", payload))
        mode = GovernanceMode(
            payload.get("mode", GovernanceMode.read_only_firewall.value)
        )
        token = (
            CapabilityToken.model_validate(payload["token"])
            if payload.get("token")
            else None
        )
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    # Unauthenticated simulation route: dry-run so it cannot mutate posture or
    # write to the stores. Minting a capability token (the actual authorization)
    # goes through the guarded /v1/mcp/metasploit/token.
    outcome = runtime.evaluate_metasploit(intent, mode=mode, token=token, record=False)
    return {
        "decision": outcome.decision,
        "evidence": outcome.evidence,
        "simulated": outcome.simulated,
        "severe": outcome.severe,
        "posture": runtime.posture,
    }


@app.post("/v1/mcp/metasploit/token", dependencies=[ControlPlaneAuth])
def metasploit_token(payload: dict[str, Any]) -> CapabilityToken:
    """
    Mint a capability token for a validated Metasploit intent.
    
    Parameters:
        payload (dict[str, Any]): Request data containing an ``intent`` and optional
            ``approver`` and ``ttl_seconds`` values.
    
    Returns:
        CapabilityToken: The minted capability token.
    
    Raises:
        HTTPException: With status code 422 when the intent is missing or the
            provided intent or token lifetime is invalid.
    """
    if "intent" not in payload:
        raise HTTPException(status_code=422, detail="missing 'intent' in payload")
    try:
        intent = MetasploitIntent.model_validate(payload["intent"])
        # TypeError, not just ValueError: int(None) and int({}) raise TypeError,
        # so a null or object ttl_seconds would otherwise escape as a 500 while
        # a non-numeric string correctly returned 422.
        ttl_seconds = int(payload.get("ttl_seconds", 600))
    except (ValidationError, TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return runtime.metasploit.mint_token(
        intent,
        approver=payload.get("approver", "human:operator"),
        ttl_seconds=ttl_seconds,
    )


@app.get("/v1/persistence/summary")
def persistence_summary() -> dict[str, Any]:
    """Return a summary of the runtime's persisted state.
    
    Returns:
    	dict[str, Any]: A summary of the persisted runtime state.
    """
    return runtime.persisted_summary()


@app.get("/v1/recovered-state")
def recovered_state() -> dict[str, Any]:
    # Rebuilt from the persisted decision log, not from live runtime state, so
    # the response is meaningful after a restart.
    """Reconstruct the runtime state from the persisted decision log.
    
    Returns:
    	dict[str, Any]: The recovered runtime state."""
    return asdict(ReplayEngine().recover())


@app.get("/v1/policies")
def list_policies() -> dict[str, Any]:
    """Return all stored policy rules."""
    return {"rules": [rule.model_dump() for rule in runtime.policy_store.list()]}


@app.put("/v1/policies/{rule_id}", dependencies=[ControlPlaneAuth])
def upsert_policy(rule_id: str, rule: PolicyRule) -> PolicyRule:
    """Create or update a policy rule using the identifier from the request path.
    
    Parameters:
    	rule_id (str): Identifier to assign to the policy rule.
    	rule (PolicyRule): Policy rule to store.
    
    Returns:
    	PolicyRule: The stored policy rule.
    """
    if rule.id != rule_id:
        rule = rule.model_copy(update={"id": rule_id})
    return runtime.policy_store.upsert(rule)


@app.delete("/v1/policies/{rule_id}", dependencies=[ControlPlaneAuth])
def delete_policy(rule_id: str) -> dict[str, Any]:
    """Delete the policy rule identified by the specified ID.
    
    Parameters:
    	rule_id (str): Identifier of the policy rule to delete.
    
    Returns:
    	dict[str, Any]: A mapping containing whether the policy rule was deleted.
    """
    return {"deleted": runtime.policy_store.delete(rule_id)}
