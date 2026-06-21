from urllib.parse import urlparse
from .schemas import Decision, PolicyDecision, PolicyRequest, Posture

NETWORK_ACTIONS = {'http.request', 'api.call', 'mcp.invoke', 'package.install'}

def host(target):
    p=urlparse(target)
    return (p.hostname or target.split('/')[0]).lower()

def allowed(h, patterns):
    return any(h==p.lower() or (p.startswith('*.') and h.endswith(p[1:].lower())) for p in patterns)

def rule_matches(rule, req:PolicyRequest):
    if rule.action!='*' and rule.action!=req.action:
        return False
    if rule.target=='*':
        return True
    is_network = req.action in NETWORK_ACTIONS
    target_value = host(req.target) if is_network else req.target
    rule_target = host(rule.target) if is_network else rule.target
    return allowed(target_value, [rule_target])

class PolicyEngine:
    def evaluate(self, req:PolicyRequest, env_name, profile, posture, policy_rules=()):
        if posture==Posture.locked:
            return self.deny(req, env_name, posture, 'runtime locked', 'posture.locked')
        for rule in policy_rules:
            if rule.action=='*' or rule.target=='*':
                continue
            if rule_matches(rule, req):
                return PolicyDecision(decision=rule.effect, actor=req.actor, action=req.action, target=req.target, environment=env_name, posture=posture, reason=rule.reason, matched_rule=f'policy.{rule.id}')
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
