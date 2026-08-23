from __future__ import annotations

from superbot_api.domain.enums import RiskLevel, ToolDecision


def default_decision_for_risk(risk: RiskLevel) -> tuple[ToolDecision, str]:
    if risk is RiskLevel.READ:
        return ToolDecision.ALLOW, "read-only action"
    if risk is RiskLevel.CRITICAL:
        return ToolDecision.REQUIRE_APPROVAL, "critical action always requires approval"
    return ToolDecision.REQUIRE_APPROVAL, f"{risk.value} action requires approval"
