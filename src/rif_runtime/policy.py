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
    p = urlparse(target)
    return (p.hostname or target.split("/")[0]).lower()


def allowed(h: str, patterns: Iterable[str]) -> bool:
    return any(
        h == p.lower() or (p.startswith("*.") and h.endswith(p[1:].lower()))
        for p in patterns
    )


def rule_matches(rule: PolicyRule, req: PolicyRequest) -> bool:
    """Determine whether a policy rule matches a request.
    
    Parameters:
    	rule (PolicyRule): The policy rule to evaluate.
    	req (PolicyRequest): The request to compare with the rule.
    
    Returns:
    	bool: `true` if the rule's action and target match the request, `false` otherwise.
    """
    if rule.action != "*" and rule.action != req.action:
        return False
    if rule.target == "*":
        return True
    is_network = req.action in NETWORK_ACTIONS
    target_value = host(req.target) if is_network else req.target
    rule_target = host(rule.target) if is_network else rule.target
    return allowed(target_value, [rule_target])


def is_catch_all(rule: PolicyRule) -> bool:
    """
    Determine whether a policy rule matches every action and target.
    
    Parameters:
        rule (PolicyRule): The policy rule to inspect.
    
    Returns:
        bool: `true` if the rule's action and target are both `"*"`, `false` otherwise.
    """
    return rule.action == "*" and rule.target == "*"


def specificity(rule: PolicyRule) -> int:
    """
    Determine how specifically a policy rule selects an action and target.
    
    Returns:
    	int: The number of concrete selectors, from 0 to 2.
    """
    return int(rule.action != "*") + int(rule.target != "*")


def ordered_rules(rules: Iterable[PolicyRule]) -> list[PolicyRule]:
    """
    Order selective policy rules from most to least specific.
    
    Parameters:
    	rules (Iterable[PolicyRule]): Policy rules to order.
    
    Returns:
    	list[PolicyRule]: Selective rules ordered by descending specificity, with catch-all rules omitted.
    """
    return sorted(
        (rule for rule in rules if not is_catch_all(rule)),
        key=specificity,
        reverse=True,
    )


def catch_all_rules(rules: Iterable[PolicyRule]) -> list[PolicyRule]:
    """Catch-all rules in configured order."""
    return [rule for rule in rules if is_catch_all(rule)]


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
        Evaluate a policy request against posture, policy rules, and environment constraints.
        
        Parameters:
            req (PolicyRequest): Request context and action to evaluate.
            env_name (str): Name of the environment associated with the request.
            profile (EnvironmentProfile): Environment permissions and network restrictions.
            posture (Posture): Current runtime security posture.
            policy_rules (Sequence[PolicyRule]): Configured selective and catch-all policy rules.
        
        Returns:
            PolicyDecision: The resulting allow or deny decision, including the matching rule and reason.
        """
        if posture == Posture.locked:
            return self.deny(req, env_name, posture, "runtime locked", "posture.locked")
        # Selective rules run before the environment constraints below: an
        # operator naming an action/target pair is stating an intent that
        # overrides the profile default (see
        # test_custom_allow_rule_overrides_network_denial). Catch-alls do not
        # get that power -- they are applied at the bottom of this method.
        for rule in ordered_rules(policy_rules):
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
        # Catch-all rules are the configured fallback, replacing the built-in
        # default.allow. Deliberately last: a "*"/"*" rule states what to do
        # with everything not otherwise decided, so letting it run earlier
        # would let a single broad allow disable the host allowlist above.
        for rule in catch_all_rules(policy_rules):
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
