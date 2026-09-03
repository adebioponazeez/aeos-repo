# PART III — ECONOMICS

## Chapter 8. Accounting: Cost That Cannot Hide

The founding spec's objective function — **OUTCOME VALUE / HUMAN
ATTENTION** — cannot be optimized by a system that never measures it.
v4's `economics.py` makes the measurement structural.

`CostTracker` records every model's token usage per task at list-price
rates and reports totals, per-task breakdowns, and budget states. The
deterministic engine costs 0.0 by construction, and the demo is honest
about being a demo: the reference bundle's economics note says the
figures are list-price estimates on model hints, because honest
accounting includes honesty about simulation (`test_echo_is_free` is,
in its small way, an integrity test).

`Budget` speaks the governor's grammar on purpose: **ALLOW** under
80% of budget, **CHECKPOINT** in the final 20% — the system tells you
it is approaching the cliff while there is still time to decide — and
**DENY** at exhaustion (`test_budget_escalates_then_denies`). Spending
authority and action authority flow through the same decision
vocabulary, so a budgeted agent fleet composes with the autonomy
ladder instead of fighting it.

## Chapter 9. Leverage: The Ratio That Names the Book

`leverage_ratio(outcomes, interventions)` is the objective function as
a function. Interventions are counted from the event log — checkpoints
the human resolved plus escalations — because leverage the system
*assigns itself* is marketing; leverage computed from what the human
actually had to touch is a measurement.

The reference run's number: **7.0** — seven verified outcomes, zero
human interventions. The honest edge cases are part of the design:
zero interventions with zero outcomes is `None`, not zero, because a
ratio over an empty denominator is a lie; and the fully-supervised
limit (N interventions, N outcomes) converges toward 1.0, which is
precisely the "AI as fancy autocomplete" regime the whole architecture
exists to escape.

The economic reading of the seven versions: v1 bought leverage
mechanisms; v2 bought leverage that survives crashes; v4 made the
leverage *legible*; v6–v7 make it compound — the factory's installed
capabilities are leverage that manufactures leverage. Ten-million-x is
not a number anyone hits by going faster. It is what compounding looks
like when the rungs are real.
