# ADR-014: Economics as a first-class layer

**Status: ACCEPTED (v4.0)**

## Context
The founding spec's objective function — OUTCOME VALUE / HUMAN
ATTENTION — cannot be optimized if it is never measured. Cost that is
never accounted is cost that compounds silently.

## Decision
`CostTracker` records per-task, per-model token usage at list-price
rates (the deterministic engine costs 0.0 by construction — honest
accounting includes honesty about simulation). `Budget` speaks the
same grammar as the governor: ALLOW → CHECKPOINT at 80% → DENY at
100%. `leverage_ratio` computes the objective function from real
event-log interventions (checkpoints resolved + escalations), and
refuses to fabricate a denominator: zero interventions with zero
outcomes is `None`, not zero.

## Alternatives
- Vendor dashboards: rejected — post-hoc, outside the harness, outside
  the audit trail.

## Tradeoffs
(+) Budget enforcement composes with autonomy governance.
(−) Rates are configuration; simulated usage in demos is labeled as
such in the evidence bundle.

## Consequences
Reference run evidence: `leverage: 7.0` (7 outcomes, 0 interventions),
cost $30.26 list-price estimate on model hints.
