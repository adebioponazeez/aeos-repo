# ADR-054: The Reckoning — audit before more capability

**Status: ACCEPTED (v39.7.1)**

## Context

The operator's challenge: "why is everything disjointed... why is
almost everything built so far less than 40% of what it should
be, done thoroughly, end-to-end?" This followed 39 versions
shipped at a cadence of one capability per directive, each with
green receipts — and it demanded an answer with evidence, not a
defense.

## Findings (the full report is docs/STATE-OF-AEOS.md)

1. **The disjointedness is real and measurable.** Walking the
   spine an operator would take (intent → plan → execute → real
   model → evidence → learning → live view → holdout → closing
   the loop), 3.5 of 9 steps work end-to-end: **~39%**. The
   operator's estimate was accurate.
2. **Root cause: the cadence.** Version-per-directive optimized
   for NEW capability + module-level receipts. Nothing forced the
   last capability to be integrated before the next shipped;
   integration work produces no ladder row and lost every
   scheduling conflict.
3. **The receipts were narrow, not dishonest.** Scribe, doctor,
   gauntlets and CI proved what EXISTS is truthful and tested;
   none of them asked whether the parts COMPOSE. Both things were
   true at once: "27/27 gauntlet green" and "the graph language
   and the reference pipeline never meet."
4. **Latent defects survived 577 tests** (found by this audit's
   hygiene sweep, all fixed): an unbound name on a never-exercised
   failure path (storm blackout), a short-circuit-guarded dead
   line (pipeline), a quoted annotation with no import
   (evaluation).
5. **The deepest gap:** no real model has ever executed a task
   through the system. Every end-to-end receipt was deterministic
   EchoModel — honestly disclosed, never closed.

## Decision

1. **The treadmill is off.** No new capability ships until the
   SPINE is one command end-to-end: a DOT graph executing on the
   reference pipeline (not a demo roster), producing a bundle,
   feeding memory, streaming live, holdout-verdicted, receipted.
2. **The demo path is a product path or it is a lie.** One shared
   demo factory; graph runs write live event sinks the shopfloor
   can stream (done in this release, regression-tested).
3. **Hygiene is law:** pyflakes-clean at zero, permanently — CI
   may adopt the check.
4. **First Light requires the operator.** The first real model
   call through the spine happens only on explicit opt-in
   (paywall law); the receipt will disclose model, cost, latency.
5. **Audits are releases too.** This audit ships as v39.7.1 with
   its findings, fixes, and the plan (Spine → First Light →
   Front Door Diet → Outside Eyes) — because an audit that does
   not ship is a PDF, and this project does not ship PDFs.

## Consequences

- The README now leads with the honest state (~85% mechanism
  coverage, ~39% end-to-end) instead of the version ladder.
- The ladder compresses to milestones; CHANGELOG keeps the
  history.
- Every future receipt should name which SPINE STEPS it advanced,
  not only which patterns it closed.
