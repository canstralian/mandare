from collections.abc import Iterable, Sequence
from urllib.parse import urlparse

from .configuration.policies import PolicyRule
from .schemas import (
    Decision,
    EnvironmentProfile,
    PolicyDecision,
    PolicyRequest,
    Posture,
)

NETWORK_ACTIONS = {"http.request", "api.call", "mcp.invoke", "package.install"}


def host(target: str) -> str:
    """Extract the lowercase hostname from a URL or target string.
    
    Parameters:
    	target (str): URL or network target to parse.
    
    Returns:
    	str: The lowercase hostname, or the first path segment when no hostname is available.
    """
    p = urlparse(target)
    return (p.hostname or target.split("/")[0]).lower()


def allowed(h: str, patterns: Iterable[str]) -> bool:
    """
    Determine whether a hostname matches any allowed host pattern.
    
    Parameters:
    	h (str): Hostname to evaluate.
    	patterns (Iterable[str]): Hostnames or wildcard patterns to compare against.
    
    Returns:
    	bool: `true` if the hostname matches an exact or `*.` wildcard pattern, `false` otherwise.
    """
    return any(
        h == p.lower() or (p.startswith("*.") and h.endswith(p[1:].lower()))
        for p in patterns
    )


def rule_matches(rule: PolicyRule, req: PolicyRequest) -> bool:
    """
    Determine whether a policy rule matches a request's action and target.
    
    Parameters:
        rule (PolicyRule): Policy rule to evaluate.
        req (PolicyRequest): Request to compare with the rule.
    
    Returns:
        bool: `true` if the rule matches the request, `false` otherwise.
    """
    if rule.action != "*" and rule.action != req.action:
        return False
    if rule.target == "*":
        return True
    is_network = req.action in NETWORK_ACTIONS
    target_value = host(req.target) if is_network else req.target
    rule_target = host(rule.target) if is_network else rule.target
    return allowed(target_value, [rule_target])


class PolicyEngine:
    def evaluate(
        self,
        req: PolicyRequest,
        env_name: str,
        profile: EnvironmentProfile,
        posture: Posture,
        policy_rules: Sequence[PolicyRule] = (),
    ) -> PolicyDecision:
        """
        Evaluate a policy request against the current posture, environment profile, and policy rules.
        
        Parameters:
            req (PolicyRequest): Request to evaluate.
            env_name (str): Name of the environment associated with the request.
            profile (EnvironmentProfile): Environment settings governing network and package access.
            posture (Posture): Current runtime security posture.
            policy_rules (Sequence[PolicyRule]): Specific policy rules to consider.
        
        Returns:
            PolicyDecision: The resulting allow or deny decision, including its reason and matched rule.
        """
        if posture == Posture.locked:
            return self.deny(req, env_name, posture, "runtime locked", "posture.locked")
        for rule in policy_rules:
            if rule.action == "*" or rule.target == "*":
                continue
            if rule_matches(rule, req):
                return PolicyDecision(
                    decision=rule.effect,
                    actor=req.actor,
                    action=req.action,
                    target=req.target,
                    environment=env_name,
                    posture=posture,
                    reason=rule.reason,
                    matched_rule=f"policy.{rule.id}",
                )
        if (
            req.action == "package.install"
            and not profile.allow_package_manager_network_access
        ):
            return self.deny(
                req,
                env_name,
                Posture.elevated,
                "package manager egress disabled",
                "package.egress.disabled",
            )
        if (
            req.action.startswith("mcp.")
            and not profile.allow_mcp_server_network_access
        ):
            return self.deny(
                req,
                env_name,
                Posture.elevated,
                "MCP egress disabled",
                "mcp.egress.disabled",
            )
        if req.action in {"http.request", "api.call", "mcp.invoke", "package.install"}:
            h = host(req.target)
            if profile.networking_type == "limited" and not allowed(
                h, profile.allowed_hosts
            ):
                return self.deny(
                    req,
                    env_name,
                    Posture.elevated,
                    f"host denied: {h}",
                    "network.host.denied",
                )
        return PolicyDecision(
            decision=Decision.allow,
            actor=req.actor,
            action=req.action,
            target=req.target,
            environment=env_name,
            posture=posture,
            reason="allowed by constraints",
            matched_rule="default.allow",
        )

    def deny(
        self,
        req: PolicyRequest,
        env_name: str,
        posture: Posture,
        reason: str,
        rule: str,
    ) -> PolicyDecision:
        """
        Create a deny decision for a policy request.
        
        Parameters:
        	req (PolicyRequest): The request to deny.
        	env_name (str): The environment associated with the request.
        	posture (Posture): The current security posture.
        	reason (str): The reason for denying the request.
        	rule (str): The identifier of the matching policy rule.
        
        Returns:
        	PolicyDecision: A denial decision containing the request context and supplied policy details.
        """
        return PolicyDecision(
            decision=Decision.deny,
            actor=req.actor,
            action=req.action,
            target=req.target,
            environment=env_name,
            posture=posture,
            reason=reason,
            matched_rule=rule,
        )
