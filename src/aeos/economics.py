"""v4.0 — Economics: the OS accounts for what it spends and earns.

Cost per task from token accounting; budgets that gate spending with
the same ALLOW/CHECKPOINT/DENY grammar as the governor; and the
founding metric — OUTCOME VALUE / HUMAN ATTENTION — computed from what
actually happened in the event log, not from a dashboard fantasy.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import Decision

# per-1k-token rates (USD). echo-1 is free by construction.
RATES_PER_1K: dict[str, tuple[float, float]] = {
    "echo-1": (0.0, 0.0),
    "default": (0.15, 0.60),
    "reasoning": (3.0, 15.0),
    "long-context": (1.25, 5.0),
    "provider-1": (0.5, 1.5),
    "provider-2": (0.5, 1.5),
}


@dataclass
class Usage:
    model: str
    tokens_in: int
    tokens_out: int
    task: str = ""


@dataclass
class CostTracker:
    usages: list[Usage] = field(default_factory=list)

    def record(self, model: str, tokens_in: int, tokens_out: int,
               task: str = "") -> Usage:
        u = Usage(model=model, tokens_in=tokens_in, tokens_out=tokens_out,
                  task=task)
        self.usages.append(u)
        return u

    def cost(self, usage: Usage) -> float:
        rin, rout = RATES_PER_1K.get(usage.model, RATES_PER_1K["default"])
        return usage.tokens_in / 1000 * rin + usage.tokens_out / 1000 * rout

    def total_cost(self) -> float:
        return round(sum(self.cost(u) for u in self.usages), 6)

    def total_tokens(self) -> int:
        return sum(u.tokens_in + u.tokens_out for u in self.usages)

    def per_task(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for u in self.usages:
            out[u.task] = round(out.get(u.task, 0.0) + self.cost(u), 6)
        return out


@dataclass
class Budget:
    max_cost: float
    max_tokens: int = 10_000_000

    def check(self, tracker: CostTracker) -> tuple[Decision, str]:
        tokens = tracker.total_tokens()
        cost = tracker.total_cost()
        if tokens >= self.max_tokens:
            return Decision.DENY, f"token budget exhausted ({tokens}/{self.max_tokens})"
        if cost >= self.max_cost * 0.8 and cost < self.max_cost:
            return Decision.CHECKPOINT, (f"cost {cost:.4f} within 20% of "
                                          f"budget {self.max_cost}")
        if cost >= self.max_cost:
            return Decision.DENY, f"cost budget exhausted ({cost:.4f}/{self.max_cost})"
        return Decision.ALLOW, f"cost {cost:.4f}/{self.max_cost}, tokens {tokens}"


def leverage_ratio(tasks_completed: int, human_interventions: int) -> float | None:
    """OUTCOME VALUE / HUMAN ATTENTION. Interventions = checkpoints the
    human actually resolved + escalations. None when nothing happened —
    a ratio over an empty denominator is a lie."""
    if human_interventions <= 0:
        return None if tasks_completed == 0 else float(tasks_completed)
    return round(tasks_completed / human_interventions, 3)


def interventions_from_events(events: list) -> tuple[int, int]:
    """Count (checkpoints-resolved, escalations) from an EventLog's events."""
    checkpoints = sum(1 for e in events if e.kind.startswith("governor.checkpoint"))
    escalations = sum(1 for e in events if e.kind.startswith("task.escalated"))
    return checkpoints, escalations
