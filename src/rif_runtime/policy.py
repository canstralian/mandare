from urllib.parse import urlparse
from .schemas import Decision, PolicyDecision, PolicyRequest, Posture

def host(target):
    p=urlparse(target)
    return (p.hostname or target.split('/')[0]).lower()

def allowed(h, patterns):
    return any(h==p.lower() or (p.startswith('*.') and h.endswith(p[1:].lower())) for p in patterns)

class PolicyEngine:
    def evaluate(self, req:PolicyRequest, env_name, profile, posture):
        if posture==Posture.locked:
            return self.deny(req, env_name, posture, 'runtime locked', 'posture.locked')
        if req.action=='package.install' and not profile.allow_package_manager_network_access:
            return self.deny(req, env_name, Posture.elevated, 'package manager egress disabled', 'package.egress.disabled')
        if req.action.startswith('mcp.') and not profile.allow_mcp_server_network_access:
            return self.deny(req, env_name, Posture.elevated, 'MCP egress disabled', 'mcp.egress.disabled')
        if req.action in {'http.request','api.call','mcp.invoke','package.install'}:
            h=host(req.target)
            if profile.networking_type=='limited' and not allowed(h, profile.allowed_hosts):
                return self.deny(req, env_name, Posture.elevated, f'host denied: {h}', 'network.host.denied')
        return PolicyDecision(decision=Decision.allow, actor=req.actor, action=req.action, target=req.target, environment=env_name, posture=posture, reason='allowed by constraints', matched_rule='default.allow')

    def deny(self, req, env_name, posture, reason, rule):
        return PolicyDecision(decision=Decision.deny, actor=req.actor, action=req.action, target=req.target, environment=env_name, posture=posture, reason=reason, matched_rule=rule)
