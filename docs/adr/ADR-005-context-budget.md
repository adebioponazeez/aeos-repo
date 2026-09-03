# ADR-005: Context is a budgeted, expiring resource

**Status: ACCEPTED (v0.3)**

## Context
Spec §9 plus 2026 field evidence: context rot is measured; bloated
context files demonstrably reduce agent success (Gloaguen et al.,
138 repos). "More context is better" is false and expensive.

## Decision
Every `ContextUnit` carries tier (ESSENTIAL…UNKNOWN), authority,
expiry, and conflict keys. `assemble()` runs under a token budget:
stale units drop loudly, irrelevant tiers never enter, overflow drops
the lowest tier first and RECORDS every drop with a reason; an
ESSENTIAL unit that cannot fit is a hard flag ("compress or raise
budget") rather than silent truncation; conflicting authorities are
surfaced, never averaged away. `progressive_disclosure()` returns an
index (first line per unit) — bodies on demand.

## Alternatives considered
- **RAG-over-everything** — rejected as a default: retrieval without
  classification just relocates the dumping problem and hides the
  drop decisions.

## Tradeoffs
(+) Every context decision is explainable from the assembly log.
(−) Token math is approximate (len/4) — deliberately
provider-independent.

## Consequences
Agents get just-in-time context, and the OS can always answer "why did
the model see this?" from the assembly log.
