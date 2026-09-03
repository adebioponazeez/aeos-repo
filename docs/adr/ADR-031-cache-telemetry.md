# ADR-031: Payoff must be readable

**Status: ACCEPTED (v22.0)**

## Context
v14 made prefixes byte-stable and priced memory in tokens, but cache
payoff was asserted, not read. Best-in-class providers report usage;
we were ignoring the receipt.

## Decision
`telemetry.py` parses provider usage blocks (Anthropic-style fields)
into `UsageSnapshot`: cache hit rate, effective input tokens (reads
discounted 0.9x). Missing or malformed usage returns None — silence,
never invention. Live mode requires AEOS_LIVE=1 opt-in; fixtures are
labeled fixtures.

## Consequences
`test_cache_reads_cut_effective_tokens`,
`test_missing_usage_is_none_not_invented`,
`test_live_mode_requires_opt_in`.
