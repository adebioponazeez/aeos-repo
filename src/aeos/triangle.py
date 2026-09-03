"""v13.0 — The Triangle: Control / Cost / Speed as one dial, measured.

The thumbnail's law is real: MORE CONTROL = LESS SPEED, CONTROL COSTS
SPEED. Pretending to maximize all three is the defining amateur error
of agentic engineering. The operating layer's job is not to defeat the
triangle — it is to make the trade EXPLICIT, DIALABLE, and MEASURED:

  RunProfile   one named stance (CONTROL / BALANCED / SPEED / COST)
               that moves every knob TOGETHER: autonomy ceiling, gate
               set, parallelism, sandbox isolation, fusion, budget,
               model route
  floors       what no profile may touch: boundaries, checkpoint-
               forever classes, core gates, evidence-gated memory —
               the triangle bends, the law does not
  TriangleReport  the measured trade, computed from what a run ACTUALLY
               did (event log + economics + clock), not what it intended

ADR-022: the tradeoff is policy with a receipt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts import AutonomyLevel, Decision


# ------------------------------------------------------------- profiles

PROFILE_PRESETS: dict[str, dict[str, Any]] = {
    "control": {
        "label": "CONTROL — verify everything, ask often, run slower",
        "autonomy_ceiling": AutonomyLevel.L3_CHECKPOINTED_AUTONOMY,
        "max_workers": 2,
        "strict_gates": True,        # + schema, tests_pass, regression
        "isolation": "process",      # factory sandboxes in subprocesses
        "fusion": True,              # N opinions before the gate
        "budget_usd": 5.0,
        "model_route": "reasoning",
        "timeout_s": 180.0,
    },
    "balanced": {
        "label": "BALANCED — the production default (v1–v12 behavior)",
        "autonomy_ceiling": AutonomyLevel.L4_GUARDED_AUTONOMY,
        "max_workers": 4,
        "strict_gates": False,
        "isolation": "inprocess",
        "fusion": False,
        "budget_usd": 2.0,
        "model_route": "default",
        "timeout_s": 120.0,
    },
    "speed": {
        "label": "SPEED — parallel wide, cheap-fast models, lean (not naked) gates",
        "autonomy_ceiling": AutonomyLevel.L5_CONTINUOUS_AUTONOMY,
        "max_workers": 8,
        "strict_gates": False,
        "isolation": "inprocess",
        "fusion": False,
        "budget_usd": 3.0,
        "model_route": "fast",
        "timeout_s": 60.0,
    },
    "cost": {
        "label": "COST — smallest bill that still passes the floors",
        "autonomy_ceiling": AutonomyLevel.L4_GUARDED_AUTONOMY,
        "max_workers": 4,
        "strict_gates": False,
        "isolation": "inprocess",
        "fusion": False,             # fusion multiplies spend — off
        "budget_usd": 0.25,
        "model_route": "cheap",
        "timeout_s": 120.0,
    },
}

# The floor: gate names no profile may remove. Safety is not a knob.
FLOOR_GATES = {"artifacts_exist", "claims_are_backed"}


@dataclass
class RunProfile:
    name: str
    label: str
    autonomy_ceiling: AutonomyLevel
    max_workers: int
    strict_gates: bool
    isolation: str
    fusion: bool
    budget_usd: float
    model_route: str
    timeout_s: float
    overrides: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def preset(cls, name: str, **overrides: Any) -> "RunProfile":
        if name not in PROFILE_PRESETS:
            raise ValueError(f"unknown profile '{name}' — "
                             f"known: {sorted(PROFILE_PRESETS)}")
        d = dict(PROFILE_PRESETS[name])
        label = d.pop("label")
        d.update(overrides)
        p = cls(name=name, label=label, **d)
        problems = p.validate()
        if problems:
            raise ValueError("; ".join(problems))
        return p

    def validate(self) -> list[str]:
        problems: list[str] = []
        if self.max_workers < 1 or self.max_workers > 16:
            problems.append("max_workers must be in [1, 16]")
        if self.budget_usd <= 0:
            problems.append("budget must be positive — free is not a stance")
        if self.timeout_s <= 0:
            problems.append("timeout must be positive")
        if self.autonomy_ceiling.value > AutonomyLevel.L5_CONTINUOUS_AUTONOMY.value:
            problems.append("no profile may start above L5 — L6/L7 are "
                            "earned by evidence, never selected")
        return problems

    def gate_names(self, stock: list[str], strict_extra: list[str]) -> list[str]:
        """Ordered gate list for the stance — floors always survive."""
        names = list(stock)
        if self.strict_gates:
            for g in strict_extra:
                if g not in names:
                    names.append(g)
        for floor in FLOOR_GATES:          # the law, re-applied last
            if floor not in names:
                names.append(floor)
        return names

    def summary(self) -> dict[str, Any]:
        return {"name": self.name, "label": self.label,
                "autonomy_ceiling": self.autonomy_ceiling.name,
                "max_workers": self.max_workers,
                "strict_gates": self.strict_gates,
                "isolation": self.isolation, "fusion": self.fusion,
                "budget_usd": self.budget_usd,
                "model_route": self.model_route,
                "floor_gates": sorted(FLOOR_GATES)}


# ------------------------------------------------------------ measuring

@dataclass
class TriangleReport:
    profile: str
    control: float          # 0..1 — measured, componented
    cost_usd: float
    speed_tasks_per_s: float
    duration_s: float
    components: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        c = self.components
        lines = [
            f"TRIANGLE — profile '{self.profile}' (measured, not intended)",
            f"  CONTROL {self.control:.2f}/1.00   "
            f"gates/run={c.get('gate_checks', 0)}  "
            f"boundaries={c.get('boundaries_enforced', 0)}  "
            f"checkpoints={c.get('checkpoints', 0)}  "
            f"isolation={c.get('isolation', '-')}  fusion={c.get('fusion', False)}",
            f"  COST    ${self.cost_usd:.4f}      "
            f"tokens={c.get('tokens', 0)}  budget=${c.get('budget_usd', 0)}",
            f"  SPEED   {self.speed_tasks_per_s:.2f} tasks/s  "
            f"duration={self.duration_s:.2f}s  waves={c.get('waves', 0)}  "
            f"workers={c.get('max_workers', '?')}",
        ]
        lines.append("  THE TRADE: " + c.get("trade", "—"))
        return "\n".join(lines)


def measure_triangle(*, profile: RunProfile, events: list,
                     cost_usd: float, tokens: int, duration_s: float,
                     tasks: int, waves: int,
                     isolation_used: str | None = None) -> TriangleReport:
    """Compute the measured triangle from a run's actual artifacts."""
    kinds = [e.kind for e in events]
    gate_checks = sum(1 for k in kinds if k.startswith("gate.checked"))
    boundaries = sum(1 for k in kinds if k.startswith("boundary"))
    checkpoints = sum(1 for k in kinds if k.startswith("governor.checkpoint"))
    escalations = sum(1 for k in kinds if k.startswith("task.escalated"))

    # control: density of verification and permission friction, 0..1
    gates_score = min(1.0, gate_checks / max(1, tasks))          # per-task gates
    boundary_score = 1.0 if boundaries >= max(1, tasks // 2) else boundaries / max(1, tasks)
    friction = min(1.0, (checkpoints + escalations) / max(1, tasks))
    iso_score = 1.0 if (isolation_used or profile.isolation) == "process" else 0.4
    control = round(0.40 * gates_score + 0.25 * boundary_score
                    + 0.20 * friction + 0.15 * iso_score, 3)

    tps = round(tasks / duration_s, 3) if duration_s > 0 else 0.0
    if profile.name == "control":
        trade = (f"bought verification ({gate_checks} gate checks, "
                 f"{checkpoints} checkpoints) — paid with "
                 f"{duration_s:.2f}s and ${cost_usd:.4f}")
    elif profile.name == "speed":
        trade = (f"bought {tps:.2f} tasks/s — paid with autonomy "
                 f"L{profile.autonomy_ceiling.value} and lean gates")
    elif profile.name == "cost":
        trade = f"capped at ${profile.budget_usd:.2f} — paid with patience"
    else:
        trade = "the default trade — no axis maximized, none ignored"

    return TriangleReport(
        profile=profile.name, control=control, cost_usd=round(cost_usd, 6),
        speed_tasks_per_s=tps, duration_s=round(duration_s, 3),
        components={"gate_checks": gate_checks, "boundaries_enforced": boundaries,
                    "checkpoints": checkpoints, "escalations": escalations,
                    "tokens": tokens, "budget_usd": profile.budget_usd,
                    "waves": waves, "max_workers": profile.max_workers,
                    "isolation": isolation_used or profile.isolation,
                    "fusion": profile.fusion, "trade": trade})
