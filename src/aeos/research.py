"""v5.0 — Autonomous research with untrusted-source discipline.

The researcher's law: every fact carries a source and a confidence;
anything below threshold lands in `unverified`, never in the brief's
conclusions. This is the anti-hallucination gate applied upstream of
knowledge — cheap here, expensive everywhere else.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .tools import ToolRegistry


@dataclass
class Finding:
    fact: str
    source: str
    confidence: float


@dataclass
class ResearchBrief:
    query: str
    findings: list[Finding] = field(default_factory=list)
    unverified: list[Finding] = field(default_factory=list)

    @property
    def average_confidence(self) -> float:
        return (round(sum(f.confidence for f in self.findings) / len(self.findings), 3)
                if self.findings else 0.0)


class ResearchPipeline:
    def __init__(self, tools: ToolRegistry, *, min_confidence: float = 0.7,
                 min_authority: float = 0.5) -> None:
        self.tools = tools
        self.min_confidence = min_confidence
        self.min_authority = min_authority

    def run(self, query: str, *, task_uid: str = "research") -> ResearchBrief:
        brief = ResearchBrief(query=query)
        result = self.tools.call("web_search", {"query": query},
                                 task_uid=task_uid)
        if result.is_error or not result.result:
            return brief  # no sources -> empty brief -> UNVERIFIED upstream
        for r in result.result.get("results", []):
            authority = float(r.get("authority", 0.0))
            confidence = min(0.99, authority * 0.95)  # authority caps confidence
            finding = Finding(fact=r.get("snippet", ""), source=r.get("source_id", "?"),
                              confidence=round(confidence, 3))
            if confidence >= self.min_confidence and authority >= self.min_authority:
                brief.findings.append(finding)
            else:
                brief.unverified.append(finding)
        return brief
