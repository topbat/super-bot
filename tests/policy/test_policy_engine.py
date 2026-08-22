from __future__ import annotations

from uuid import uuid4

from superbot_api.domain.enums import RiskLevel, ToolDecision
from superbot_api.policy.engine import PolicyEngine, PolicyRule, ToolInvocation


def invocation(
    tool_name: str, risk: RiskLevel, *, arguments: dict | None = None
) -> ToolInvocation:
    return ToolInvocation(
        bot_id=uuid4(), tool_name=tool_name, risk=risk, arguments=arguments or {}
    )


def test_read_tools_are_allowed_by_default() -> None:
    result = PolicyEngine([]).evaluate(invocation("files.read", RiskLevel.READ))

    assert result.decision is ToolDecision.ALLOW
    assert result.reason == "read-only action"


def test_sensitive_and_critical_actions_require_approval_by_default() -> None:
    engine = PolicyEngine([])

    assert (
        engine.evaluate(invocation("email.send", RiskLevel.SENSITIVE)).decision
        is ToolDecision.REQUIRE_APPROVAL
    )
    assert (
        engine.evaluate(invocation("payments.transfer", RiskLevel.CRITICAL)).decision
        is ToolDecision.REQUIRE_APPROVAL
    )


def test_deny_rule_overrides_allow_rule() -> None:
    engine = PolicyEngine(
        [
            PolicyRule(effect=ToolDecision.ALLOW, tool_pattern="files.*"),
            PolicyRule(effect=ToolDecision.DENY, tool_pattern="files.delete"),
        ]
    )

    result = engine.evaluate(invocation("files.delete", RiskLevel.WRITE))

    assert result.decision is ToolDecision.DENY
    assert result.matched_rule is not None


def test_allow_rule_can_be_narrowed_by_arguments() -> None:
    engine = PolicyEngine(
        [
            PolicyRule(
                effect=ToolDecision.ALLOW,
                tool_pattern="git.status",
                argument_equals={"workspace": "/workspace/reports"},
            )
        ]
    )

    allowed = engine.evaluate(
        invocation(
            "git.status", RiskLevel.WRITE, arguments={"workspace": "/workspace/reports"}
        )
    )
    outside_scope = engine.evaluate(
        invocation("git.status", RiskLevel.WRITE, arguments={"workspace": "/workspace/app"})
    )

    assert allowed.decision is ToolDecision.ALLOW
    assert outside_scope.decision is ToolDecision.REQUIRE_APPROVAL


def test_critical_action_cannot_be_permanently_allowed() -> None:
    engine = PolicyEngine(
        [PolicyRule(effect=ToolDecision.ALLOW, tool_pattern="payments.transfer")]
    )

    result = engine.evaluate(invocation("payments.transfer", RiskLevel.CRITICAL))

    assert result.decision is ToolDecision.REQUIRE_APPROVAL
    assert "critical" in result.reason

