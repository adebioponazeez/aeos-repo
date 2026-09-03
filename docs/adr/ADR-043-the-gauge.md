# ADR-043: The envelope is measured, limits are named

**Status: ACCEPTED (v34.0)**

## Context
Correctness was proven at toy scale for 33 versions; size was never
measured. Two real defects were hiding in that blind spot.

## Decision
`bench.py` + `aeos bench [--full]`: seven measured cases (memory
load, recall build+query, fleet tail, backup, groom, doctor, colony)
with LAW budgets — a blown budget fails the command. Receipts at 10k
scale: every case within budget, most with 100x+ headroom (see
docs/ENVELOPE.md). Findings fixed on the spot: (1) `EventBus.tail`
was O(N) over the stream — now an O(1) final-block seek that drops
torn fragments exactly as replay quarantines; (2) `Colony.run`
capped waves at 50, blocking legitimate 60-deep chains — the cap now
scales with graph size, cycles remain caught by the no-progress
break. Accepted limits (write-time full rewrite, linear full replay,
full FTS rebuild) are documented as named seams, not surprises.

## Consequences
`test_tail_matches_replay_at_scale`, `test_tail_beyond_block_boundary`,
`test_colony_hundred_nodes`, `test_recall_budget_holds_at_1000`.
