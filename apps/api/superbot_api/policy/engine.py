from __future__ import annotations

from fnmatch import fnmatchcase
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from superbot_api.domain.enums import RiskLevel, ToolDecision
from superbot_api.policy.risk import default_decision_for_risk


class ToolInvocation(BaseModel):
    bot_id: UUID
    tool_name: str
    risk: RiskLevel
    arguments: dict = Field(default_factory=dict)


class PolicyRule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    effect: ToolDecision
    tool_pattern: str
    bot_id: UUID | None = None
    argument_equals: dict = Field(default_factory=dict)
    enabled: bool = True

    def matches(self, invocation: ToolInvocation) -> bool:
        if not self.enabled or not fnmatchcase(invocation.tool_name, self.tool_pattern):
            return False
        if self.bot_id is not None and self.bot_id != invocation.bot_id:
            return False
        return all(
            invocation.arguments.get(key) == value
            for key, value in self.argument_equals.items()
        )


class PolicyResult(BaseModel):
    decision: ToolDecision
    reason: str
    matched_rule: UUID | None = None


class PolicyEngine:
    def __init__(self, rules: list[PolicyRule]) -> None:
        self.rules = rules

    def evaluate(self, invocation: ToolInvocation) -> PolicyResult:
        matches = [rule for rule in self.rules if rule.matches(invocation)]
        for effect in (
            ToolDecision.DENY,
            ToolDecision.REQUIRE_APPROVAL,
            ToolDecision.ALLOW,
        ):
            match = next((rule for rule in matches if rule.effect is effect), None)
            if match is None:
                continue
            if effect is ToolDecision.ALLOW and invocation.risk is RiskLevel.CRITICAL:
                return PolicyResult(
                    decision=ToolDecision.REQUIRE_APPROVAL,
                    reason="critical action cannot be permanently allowed",
                    matched_rule=match.id,
                )
            return PolicyResult(
                decision=effect,
                reason=f"matched {effect.value} rule for {match.tool_pattern}",
                matched_rule=match.id,
            )
        decision, reason = default_decision_for_risk(invocation.risk)
        return PolicyResult(decision=decision, reason=reason)
