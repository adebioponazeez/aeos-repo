"""Capability Discovery: watch the work; promote what repeats (spec §24).

The ladder: TASK -> SKILL -> AGENT -> WORKFLOW -> SERVICE ->
AUTONOMOUS CAPABILITY. Promotions are proposed from measured
frequency and validated win-rate, approved by the governor above L3.
"""

from __future__ import annotations

from collections import Counter

from .skills import SkillsRegistry


class CapabilityDiscovery:
    LADDER = ["task", "skill", "agent", "workflow", "service",
              "autonomous_capability"]

    def __init__(self, skills: SkillsRegistry) -> None:
        self.skills = skills
        self.pattern_counts: Counter[str] = Counter()

    def record_pattern(self, signature: str) -> int:
        self.pattern_counts[signature] += 1
        return self.pattern_counts[signature]

    def proposals(self) -> list[dict]:
        out = []
        for signature, count in self.pattern_counts.items():
            if count < 3:
                continue
            skill = next((s for s in self.skills.skills.values()
                          if signature.lower() in s.purpose.lower()), None)
            if skill is None:
                out.append({"signature": signature, "count": count,
                            "proposal": "task -> skill",
                            "rationale": f"repeated {count}x; codify the procedure"})
            elif skill.usage_count >= 5 and skill.win_rate >= 0.8:
                ready, _ = self.skills.promotion_candidate(skill.name)
                if ready:
                    out.append({"signature": signature, "count": count,
                                "skill": skill.name,
                                "proposal": "skill -> agent",
                                "rationale": (f"skill '{skill.name}' has "
                                              f"usage={skill.usage_count}, "
                                              f"win_rate={skill.win_rate}")})
        return out
