from fastapi import FastAPI, HTTPException
from .runtime import RIFRuntime
from .schemas import PolicyRequest, Posture
from rif_runtime.agents.auditor import AuditorAgent
from rif_runtime.configuration.policies import PolicyRule

runtime=RIFRuntime()
app=FastAPI(title='RIF Runtime', version='0.1.0')

@app.get('/health')
def health():
    return {'status':'ok','environment':runtime.environment_name,'posture':runtime.posture}

@app.get('/v1/environments')
def environments():
    return {'current':runtime.environment_name,'environments':runtime.config.environments}

@app.post('/v1/environment/{name}')
def set_environment(name:str):
    try:
        runtime.set_environment(name)
        return {'current':runtime.environment_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post('/v1/policy/evaluate')
def evaluate(req:PolicyRequest):
    return runtime.evaluate(req)

@app.post('/v1/posture/{posture}')
def posture(posture:Posture):
    runtime.posture=posture
    return {'posture':runtime.posture}

@app.get("/")
def root():
    return {
        "name": "RIF Runtime",
        "status": "online",
        "routes": ["/health", "/docs", "/v1/environments", "/v1/policy/evaluate"]
    }


@app.get("/v1/graph/summary")
def graph_summary():
    return runtime.graph_summary()

@app.get("/v1/telemetry/summary")
def telemetry_summary():
    return runtime.telemetry_summary()



@app.get("/v1/audit")
def audit():
    return AuditorAgent().audit(runtime)

@app.post("/v1/mcp/invoke")
def mcp_invoke(payload: dict):
    from rif_runtime.schemas import PolicyRequest
    req = PolicyRequest(
        actor=payload.get("actor","agent:mcp"),
        action="mcp.invoke",
        target=payload.get("target","unknown"),
        reason=payload.get("reason")
    )
    return runtime.evaluate(req)


@app.get("/v1/persistence/summary")
def persistence_summary():
    return runtime.persisted_summary()


@app.post("/v1/posture/reset")
def reset_posture():
    from rif_runtime.schemas import Posture
    runtime.posture = Posture.normal
    return {"posture": runtime.posture.value}


@app.get("/v1/recovered-state")
def recovered_state():
    return runtime.recovered_summary()


@app.get("/v1/policies")
def list_policies():
    return {"rules": [rule.model_dump() for rule in runtime.policy_store.list()]}


@app.put("/v1/policies/{rule_id}")
def upsert_policy(rule_id: str, rule: PolicyRule):
    if rule.id != rule_id:
        rule = rule.model_copy(update={"id": rule_id})
    return runtime.policy_store.upsert(rule)


@app.delete("/v1/policies/{rule_id}")
def delete_policy(rule_id: str):
    return {"deleted": runtime.policy_store.delete(rule_id)}
