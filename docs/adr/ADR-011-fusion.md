# ADR-011: Fusion — combine compute, don't select compute

**Status: ACCEPTED (v2.0)**

## Context
The fusion-harness lineage demonstrated that racing models ("A vs B")
wastes the loser while fusing N streams (architect + primary builder +
secondaries, gate-first validation) keeps every opinion and
adjudicates before merge.

## Decision
`FusionAdapter` fans one `ModelCall` to N provider adapters, clusters
replies by word-overlap majority, returns the winning text with an
`agreement` flag (AGREED/DISAGREED) and all opinions attached.
Disagreement is surfaced, never averaged: downstream gates may treat
DISAGREED as PARTIAL. Stream errors are carried as evidence, not
hidden.

## Alternatives
- Provider routing only (cheaper): kept for routine phases; fusion is
  a policy for high-stakes phases, not a global setting.

## Tradeoffs
(+) Diverse failure modes become a signal instead of a gamble.
(−) N× cost and latency — spent deliberately, per phase.

## Consequences
`test_agreement_when_streams_converge`, `test_disagreement_is_surfaced_not_averaged`.
