"""v6.0 — The meta-loop: the system improves itself inside hard bounds.

Analyze history (skill win-rates, governor behavior, entropy) and
propose improvements. Proposals are evidence-backed or stillborn.
Execution requires either L6 autonomy with reliability >= 0.98 AND a
sponsorship token — the bounds are DATA, enforced in code:

  - promotion reliability threshold may move within [0.90, 0.99]
  - the high-impact checkpoint-forever rule is IMMUTABLE
  - retirement needs >= 5 uses (enough history to condemn)

A self-improving system without floors is just a runaway system with
good intentions. The floors are the feature.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .governor import Governor
from .skills import SkillsRegistry
from .sponsorship import SponsorshipGate

SAFE_BOUNDS = {
    "promotion_threshold_min": 0.90,
    "promotion_threshold_max": 0.99,
    "retire_min_uses": 5,
    "retire_max_win_rate": 0.4,
}


@dataclass
class MetaProposal:
    kind: str                  # tune_threshold | retire_skill | adr_stub
    detail: str
    evidence: list[str]
    target: str = ""
    value: float | None = None
    uid: str = field(default_factory=lambda: f"meta-{int(time.time()*1e6):x}")


class MetaLoop:
    def __init__(self, skills: SkillsRegistry, governor: Governor) -> None:
        self.skills = skills
        self.governor = governor
        self.applied: list[str] = []
        # The live promotion threshold lives on the governor:
        governor.promotion_threshold = getattr(governor, "promotion_threshold", 0.95)

    # ---------------------------------------------------------- analyze
    def analyze(self) -> list[MetaProposal]:
        proposals: list[MetaProposal] = []
        # 1. condemn skills with enough history and a bad record
        for s in self.skills.skills.values():
            if (s.usage_count >= SAFE_BOUNDS["retire_min_uses"]
                    and s.win_rate <= SAFE_BOUNDS["retire_max_win_rate"]):
                proposals.append(MetaProposal(
                    kind="retire_skill", target=s.name,
                    detail=(f"skill '{s.name}' at win_rate={s.win_rate} over "
                            f"{s.usage_count} uses — below retirement floor"),
                    evidence=[f"usage={s.usage_count}", f"win_rate={s.win_rate}"]))
        # 2. threshold tuning from observed reliability distribution
        r = self.governor.reliability
        threshold = self.governor.promotion_threshold
        if r >= 0.99 and threshold < SAFE_BOUNDS["promotion_threshold_max"]:
            proposals.append(MetaProposal(
                kind="tune_threshold", target="promotion_threshold",
                value=round(min(threshold + 0.01,
                                SAFE_BOUNDS["promotion_threshold_max"]), 3),
                detail=(f"reliability {r} sustained — tighten promotion "
                        f"threshold {threshold} -> {min(threshold + 0.01, 0.99)}"),
                evidence=[f"reliability={r}", f"threshold={threshold}"]))
        elif r < 0.93 and threshold > SAFE_BOUNDS["promotion_threshold_min"]:
            proposals.append(MetaProposal(
                kind="tune_threshold", target="promotion_threshold",
                value=round(max(threshold - 0.01,
                                SAFE_BOUNDS["promotion_threshold_min"]), 3),
                detail=(f"reliability {r} soft — loosen promotion threshold "
                        f"toward the floor to reduce checkpoint storms"),
                evidence=[f"reliability={r}", f"threshold={threshold}"]))
        return proposals

    # ----------------------------------------------------------- apply
    def apply(self, proposal: MetaProposal, *, token: str | None,
              gate: SponsorshipGate) -> tuple[bool, str]:
        if not proposal.evidence:
            return False, "no evidence — proposal stillborn"
        scope = f"meta:{proposal.kind}:{proposal.target}"
        if not gate.authorize(token, scope):
            return False, f"refused: sponsorship required for {scope}"
        if proposal.kind == "retire_skill":
            spec = self.skills.get(proposal.target)
            if spec is None:
                return False, "target skill vanished"
            del self.skills.skills[proposal.target]
            self.applied.append(proposal.uid)
            return True, f"retired '{proposal.target}'"
        if proposal.kind == "tune_threshold":
            v = proposal.value
            if not (SAFE_BOUNDS["promotion_threshold_min"] <= v
                    <= SAFE_BOUNDS["promotion_threshold_max"]):
                return False, (f"threshold {v} outside safe bounds "
                               f"[{SAFE_BOUNDS['promotion_threshold_min']}, "
                               f"{SAFE_BOUNDS['promotion_threshold_max']}] — refused")
            self.governor.promotion_threshold = v
            self.applied.append(proposal.uid)
            return True, f"promotion_threshold -> {v}"
        return False, f"unknown proposal kind '{proposal.kind}'"

    # ------------------------------------------------------ adr stubs
    def adr_stub(self, proposal: MetaProposal, adr_dir: Path) -> Path:
        n = len(list(adr_dir.glob("ADR-*.md"))) + 9  # continue numbering
        path = adr_dir / f"ADR-{n:03d}-meta-{proposal.kind}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# ADR-{n:03d}: META {proposal.kind} — {proposal.target}\n\n"
            f"**Status: PROPOSED by meta-loop, pending human review**\n\n"
            f"## Evidence\n" + "\n".join(f"- {e}" for e in proposal.evidence) +
            f"\n\n## Detail\n{proposal.detail}\n", encoding="utf-8")
        return path
