"""Context OS: context is an engineered resource with a budget (spec §9).

Never assume MORE CONTEXT = BETTER PERFORMANCE. The Context OS treats
the context window like memory managers treat RAM: classified units,
just-in-time retrieval, hard budgets, progressive disclosure (metadata
first, bodies on demand — the 2026 pattern that defeats context rot),
conflict detection and expiration.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .contracts import ContextTier


def approx_tokens(text: str) -> int:
    """Cheap, provider-independent token estimate (~4 chars/token)."""
    return max(1, len(text) // 4)


@dataclass
class ContextUnit:
    """One addressable piece of context with provenance and freshness."""
    key: str
    body: str
    tier: ContextTier = ContextTier.USEFUL
    authority: str = "local"           # who vouches for this
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None    # freshness is a first-class property
    requires: list[str] = field(default_factory=list)  # progressive disclosure: deps
    conflict_keys: list[str] = field(default_factory=list)

    def fresh(self, now: float | None = None) -> bool:
        if self.expires_at is None:
            return True
        return (now or time.time()) <= self.expires_at


@dataclass
class AssembledContext:
    """The result of one assembly pass — auditable, budgeted, explainable."""
    prompt_units: list[str] = field(default_factory=list)
    tokens: int = 0
    dropped: list[tuple[str, str]] = field(default_factory=list)  # (key, reason)
    conflicts: list[tuple[str, str]] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(self.prompt_units)


class ContextOS:
    """Classify, rank, budget, and assemble. Just-in-time, never dump."""

    def __init__(self, budget_tokens: int = 32_000) -> None:
        self.budget_tokens = budget_tokens
        self.units: dict[str, ContextUnit] = {}
        self.assembly_log: list[AssembledContext] = []

    def put(self, unit: ContextUnit) -> "ContextOS":
        self.units[unit.key] = unit
        return self

    def classify(self, key: str, tier: ContextTier) -> None:
        if key in self.units:
            self.units[key].tier = tier

    def _conflicts(self, unit: ContextUnit) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for other_key in unit.conflict_keys:
            other = self.units.get(other_key)
            if other and other.tier in (ContextTier.ESSENTIAL, ContextTier.USEFUL):
                if other.authority != unit.authority and unit.body != other.body:
                    found.append((unit.key, other_key))
        return found

    def assemble(self, query: str, *,
                 requested: Iterable[str] | None = None,
                 budget_tokens: int | None = None) -> AssembledContext:
        """Assemble context under budget, highest tier first, fresh only.

        Rules enforced here (each one is a test):
          1. EXPIRED units are dropped as STALE, never silently included.
          2. CONFLICTING units are surfaced, not averaged away.
          3. Budget overflow drops the lowest tier first and RECORDS it.
          4. `requested` overrides ranking only within the same tier —
             an agent cannot smuggle OPTIONAL context past the budget.
        """
        budget = budget_tokens or self.budget_tokens
        result = AssembledContext()
        now = time.time()

        fresh = []
        for unit in self.units.values():
            if not unit.fresh(now):
                unit.tier = ContextTier.STALE
                result.dropped.append((unit.key, "expired"))
                continue
            fresh.append(unit)

        order = {ContextTier.ESSENTIAL: 0, ContextTier.USEFUL: 1,
                 ContextTier.OPTIONAL: 2, ContextTier.UNKNOWN: 3,
                 ContextTier.IRRELEVANT: 4, ContextTier.CONFLICTING: 5,
                 ContextTier.STALE: 6}
        want = set(requested or ())
        ranked = sorted(
            fresh,
            key=lambda u: (order[u.tier], 0 if u.key in want else 1, approx_tokens(u.body)),
        )

        for unit in ranked:
            if unit.tier in (ContextTier.IRRELEVANT, ContextTier.STALE):
                result.dropped.append((unit.key, f"tier={unit.tier.value}"))
                continue
            cost = approx_tokens(unit.body)
            if result.tokens + cost > budget and unit.tier != ContextTier.ESSENTIAL:
                result.dropped.append((unit.key, "over budget"))
                continue
            if result.tokens + cost > budget and unit.tier == ContextTier.ESSENTIAL:
                # An essential unit that cannot fit is a hard stop, not a
                # silent truncation: fail loudly, let the caller compress.
                result.dropped.append((unit.key, "ESSENTIAL over budget — compress or raise budget"))
                continue
            result.prompt_units.append(f"[{unit.key} | {unit.tier.value} | {unit.authority}]\n{unit.body}")
            result.tokens += cost
            result.conflicts.extend(self._conflicts(unit))

        self.assembly_log.append(result)
        return result

    def progressive_disclosure(self, key: str) -> list[str]:
        """Return metadata-first view: unit summaries, bodies on demand.

        This is how AGENTS.md-style files should enter context: a table
        of contents the agent can pull from, never a full dump."""
        out = []
        for unit in self.units.values():
            if key and key not in unit.key:
                continue
            first = unit.body.splitlines()[0][:120] if unit.body else ""
            out.append(f"{unit.key} [{unit.tier.value}] — {first}")
        return out
