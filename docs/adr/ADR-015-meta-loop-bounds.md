# ADR-015: The meta-loop improves the system inside hard bounds

**Status: ACCEPTED (v6.0)**

## Context
A self-improving system (L6) without floors is a runaway system with
good intentions. The failure mode is not malice — it is confident
optimization past the edge of its own evidence.

## Decision
`MetaLoop.analyze()` proposes only what data supports: skill
retirement requires ≥5 uses AND ≤0.4 win-rate; promotion-threshold
tuning is clamped to [0.90, 0.99] and refused outside; every proposal
carries its evidence or is stillborn; every application requires a
sponsorship token (ADR-013); every applied change drafts an ADR stub
for human review. The high-impact checkpoint-forever rule is
immutable — no proposal kind exists that can reach it.

## Alternatives
- Unbounded self-tuning: rejected categorically; documented as the
  anti-pattern this ADR exists to prevent.

## Tradeoffs
(+) Self-improvement that a human can audit after the fact, every time.
(−) Slower convergence than unbounded tuning — the point.

## Consequences
`test_out_of_bounds_threshold_refused_even_with_token`,
`test_apply_requires_sponsorship`, `test_adr_stub_written`.
