from __future__ import annotations

from dataclasses import dataclass


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Budget:
    max_cost_usd: float | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    max_steps: int | None = None


@dataclass(frozen=True, slots=True)
class Usage:
    cost_usd: float = 0
    input_tokens: int = 0
    output_tokens: int = 0
    steps: int = 0


def ensure_within_budget(budget: Budget, usage: Usage) -> None:
    limits = (
        ("cost", budget.max_cost_usd, usage.cost_usd),
        ("input_tokens", budget.max_input_tokens, usage.input_tokens),
        ("output_tokens", budget.max_output_tokens, usage.output_tokens),
        ("steps", budget.max_steps, usage.steps),
    )
    for name, maximum, actual in limits:
        if maximum is not None and actual > maximum:
            raise BudgetExceeded(f"{name} budget exceeded: {actual} > {maximum}")
