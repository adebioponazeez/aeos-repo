"""v9.0 — Co-architecting: the factory proposes a SLATE, humans shape it.

Template designs (v7) are safe but samey. v9 generates design VARIANTS
per signature — conservative, minimal-privilege, reviewer-first —
scores them (least privilege wins ties), sandbox-validates them all,
and hands the ranked slate to a human, who sponsors exactly one
variant. The machine explores; the human decides; the receipt has both
signatures on it (ADR-018).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .contracts import ActionClass, AgentSpec, Verdict
from .factory import design_agent
from .transport import smoke_validate


@dataclass
class DesignVariant:
    label: str
    spec: AgentSpec
    score: float = 0.0
    sandbox_verdict: Verdict = Verdict.UNVERIFIED
    rationale: str = ""

    def to_dict(self) -> dict:
        return {"label": self.label, "score": self.score,
                "verdict": self.sandbox_verdict.value,
                "rationale": self.rationale,
                "writes": self.spec.writes,
                "max_attempts": self.spec.max_attempts}


def variants_for(signature: str) -> list[DesignVariant]:
    """Three coherent philosophies of the same workload."""
    base = design_agent(signature)
    role = base.name

    conservative = base

    minimal = AgentSpec(
        name=role, mission=base.mission,
        inputs=base.inputs, outputs=base.outputs,
        tools=["fs.read"], constraints=base.constraints + [
            "single attempt only — failure escalates, never retries"],
        success_criteria=base.success_criteria,
        evaluation_criteria=base.evaluation_criteria,
        escalation_conditions=base.escalation_conditions + ["any gate failure"],
        termination_conditions=base.termination_conditions,
        writes=[], action_classes=[ActionClass.READ],
        model_hint="default")

    reviewer_first = AgentSpec(
        name=role, mission=f"{base.mission} (review-first)",
        inputs=base.inputs, outputs=base.outputs + ["review report"],
        tools=base.tools, constraints=base.constraints,
        success_criteria=base.success_criteria + [
            "review artifact exists and cites the primary artifact"],
        evaluation_criteria=base.evaluation_criteria + [
            "review artifact parses and references the work"],
        escalation_conditions=base.escalation_conditions,
        termination_conditions=base.termination_conditions,
        writes=(base.writes + [f"review/{'*'}"]) if base.writes else ["review/*"],
        action_classes=base.action_classes, model_hint="default")

    out = [
        DesignVariant("conservative", conservative,
                      rationale="the standard template: proven shape"),
        DesignVariant("minimal-privilege", minimal,
                      rationale="no write surface at all; escalates on any doubt"),
        DesignVariant("reviewer-first", reviewer_first,
                      rationale="adds an independent review artifact to the output contract"),
    ]
    for v in out:
        v.score = score_variant(v.spec)
    out.sort(key=lambda v: (-v.score, v.label))
    return out


def score_variant(spec: AgentSpec) -> float:
    """Least privilege wins ties: fewer writes, more evaluation
    criteria, more escalation off-ramps."""
    privilege = 1.0 / (1.0 + len(spec.writes))
    eval_strength = min(1.0, len(spec.evaluation_criteria) / 3.0)
    escalation = min(1.0, len(spec.escalation_conditions) / 3.0)
    return round(0.5 * privilege + 0.3 * eval_strength
                 + 0.2 * escalation, 3)


def validate_slate(slate: list[DesignVariant],
                   sandbox_root: Path) -> list[DesignVariant]:
    for i, v in enumerate(slate):
        result = smoke_validate(v.spec, sandbox_root / f"{v.label}-{i}")
        v.sandbox_verdict = Verdict(result["verdict"])
    return slate


@dataclass
class CoDesignSession:
    signature: str
    slate: list[DesignVariant] = field(default_factory=list)
    chosen: str | None = None

    def proposals(self) -> list[dict]:
        return [v.to_dict() | {"label": v.label} for v in self.slate]

    def choose(self, label: str, *, token: str | None, gate) -> tuple[bool, str]:
        variant = next((v for v in self.slate if v.label == label), None)
        if variant is None:
            return False, f"no variant '{label}' on the slate"
        if variant.sandbox_verdict is not Verdict.PASS:
            return False, (f"variant '{label}' sandbox verdict is "
                           f"{variant.sandbox_verdict.value}")
        scope = f"codesign:{variant.spec.name}:{label}"
        if not gate.authorize(token, scope):
            return False, f"refused: sponsorship required for {scope}"
        self.chosen = label
        return True, f"chose variant '{label}' for {variant.spec.name}"


def co_design(signature: str, sandbox_root: Path) -> CoDesignSession:
    session = CoDesignSession(signature=signature)
    session.slate = validate_slate(variants_for(signature), sandbox_root)
    return session
