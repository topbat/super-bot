from __future__ import annotations

import pytest
from superbot_api.policy.budget import Budget, BudgetExceeded, Usage, ensure_within_budget


def test_usage_within_every_hard_limit_is_allowed() -> None:
    ensure_within_budget(
        Budget(max_cost_usd=2, max_input_tokens=1000, max_output_tokens=500, max_steps=10),
        Usage(cost_usd=1.5, input_tokens=800, output_tokens=300, steps=8),
    )


@pytest.mark.parametrize(
    ("usage", "limit_name"),
    [
        (Usage(cost_usd=2.01), "cost"),
        (Usage(input_tokens=1001), "input_tokens"),
        (Usage(output_tokens=501), "output_tokens"),
        (Usage(steps=11), "steps"),
    ],
)
def test_each_budget_limit_is_hard(usage: Usage, limit_name: str) -> None:
    budget = Budget(max_cost_usd=2, max_input_tokens=1000, max_output_tokens=500, max_steps=10)

    with pytest.raises(BudgetExceeded, match=limit_name):
        ensure_within_budget(budget, usage)


def test_missing_limit_is_unbounded_not_zero() -> None:
    ensure_within_budget(Budget(), Usage(cost_usd=999, input_tokens=999_999, steps=999))
