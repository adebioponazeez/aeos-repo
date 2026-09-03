"""Skills OS: reusable capabilities with versioning and a promotion ladder.

The ladder (spec §24): TASK -> SKILL -> AGENT -> WORKFLOW -> SERVICE ->
AUTONOMOUS CAPABILITY. Promotion is an EVIDENCE decision computed from
measured frequency, value and win-rate — the learning loop proposes,
the skills registry adjudicates, the human approves above L3.
"""

from __future__ import annotations

from dataclasses import field
from typing import Optional

from .contracts import SkillSpec


class SkillsRegistry:
    def __init__(self) -> None:
        self.skills: dict[str, SkillSpec] = {}

    def register(self, spec: SkillSpec) -> SkillSpec:
        if spec.name in self.skills:
            existing = self.skills[spec.name]
            if _semver(spec.version) <= _semver(existing.version) and spec.origin != existing.origin:
                raise ValueError(
                    f"skill '{spec.name}' v{spec.version} must exceed existing "
                    f"v{existing.version} — regressions are not silent")
        self.skills[spec.name] = spec
        return spec

    def get(self, name: str) -> Optional[SkillSpec]:
        return self.skills.get(name)

    def record_use(self, name: str, *, won: bool) -> float:
        spec = self.skills.get(name)
        if spec is None:
            raise KeyError(name)
        spec.usage_count += 1
        wins = round(spec.win_rate * (spec.usage_count - 1)) + int(won)
        spec.win_rate = round(wins / spec.usage_count, 4)
        return spec.win_rate

    def promotion_candidate(self, name: str) -> tuple[bool, str]:
        """A skill becomes an agent-candidate when the numbers say so."""
        spec = self.skills.get(name)
        if spec is None:
            return False, "no such skill"
        if spec.usage_count >= 5 and spec.win_rate >= 0.8:
            return True, (f"usage={spec.usage_count}, win_rate={spec.win_rate} "
                          "— promote to dedicated agent")
        return False, (f"usage={spec.usage_count}, win_rate={spec.win_rate} "
                       "— below promotion threshold (needs >=5 uses, >=0.8 win)")

    def duplicates(self) -> list[tuple[str, str, float]]:
        """Entropy control: near-duplicate skills by purpose similarity."""
        names = list(self.skills)
        dups = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                sim = _similarity(self.skills[a].purpose, self.skills[b].purpose)
                if sim >= 0.6:  # MONITOR-level threshold: cheap false positives, no misses
                    dups.append((a, b, round(sim, 3)))
        return dups

    def snapshot(self) -> list[dict]:
        return [s.__dict__ | {"dependencies": list(s.dependencies),
                              "failure_modes": list(s.failure_modes)}
                for s in self.skills.values()]


def _semver(v: str) -> tuple[int, int, int]:
    try:
        major, minor, patch = (int(x) for x in v.split("."))
        return (major, minor, patch)
    except Exception:
        return (0, 0, 0)


def _similarity(a: str, b: str) -> float:
    """Jaccard similarity on word shingles — cheap, good enough for drift."""
    sa = {w for w in a.lower().split() if len(w) > 3}
    sb = {w for w in b.lower().split() if len(w) > 3}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
