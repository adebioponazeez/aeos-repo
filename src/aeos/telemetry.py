"""v22 Telemetry: cache hits are money — read them from the provider.

v14 made prefixes byte-stable (structure is the cache key); this makes
the payoff READABLE: provider usage blocks parsed into hit rates and
effective-token savings. Live metrics need a live provider — the
fixture path is honest about being a fixture.
"""
from __future__ import annotations

from dataclasses import dataclass

# cached reads bill at ~0.1x input price (provider convention)
CACHE_READ_DISCOUNT = 0.9


@dataclass
class UsageSnapshot:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    source: str = "provider"

    @property
    def cache_hit_rate(self) -> float:
        billable = (self.input_tokens + self.cache_read_tokens
                    + self.cache_creation_tokens)
        return self.cache_read_tokens / billable if billable else 0.0

    @property
    def effective_input_tokens(self) -> int:
        """What the run FELT like after the cache discount."""
        return (self.input_tokens
                + self.cache_creation_tokens
                + round(self.cache_read_tokens * (1 - CACHE_READ_DISCOUNT)))


def parse_usage(payload: dict) -> UsageSnapshot | None:
    """Anthropic-style usage block; absent/malformed -> None (silence,
    never invention)."""
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict):
        return None
    try:
        return UsageSnapshot(
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            cache_read_tokens=int(usage.get("cache_read_input_tokens", 0)),
            cache_creation_tokens=int(
                usage.get("cache_creation_input_tokens", 0)))
    except (TypeError, ValueError):
        return None


def effective_tokens(actual_tokens: int, snapshot: UsageSnapshot) -> int:
    """All-in tokens after cache discounts — the dividend, priced."""
    return max(0, actual_tokens - round(
        snapshot.cache_read_tokens * CACHE_READ_DISCOUNT))
