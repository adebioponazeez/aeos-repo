# ADR-056: Closing the loop — lessons reach the next plan

**Status: ACCEPTED (v39.9.0)**

## Context

The audit's spine step 9 verdict: "the loop closes (foreman heals,
next run improves) — PARTIAL: foreman heals workspaces, but nothing
it learns changes the next plan." Memory held lessons; learning
validated them; the distiller compressed them; the recall index
could find them — and then nothing read them before a plan ran.
The mechanism existed; the loop was open.

## Decision

1. **Recall before execution.** `_reference_run` (the one pipeline
   behind `aeos run`, `aeos run-demo` and `graph --run`) now
   recalls, before any task runs: `lesson::`, `proven::` and
   `semantic::` records whose keys name a task or agent in THIS
   plan — confidence-ordered, capped at 8 — and injects them into
   the ContextOS as `authority="memory"` units.
2. **The planner cites what it applied.** The architect handler
   collects the memory-authority units and writes them into the
   spec artifact (`spec/graph.json` → `prior_lessons`) plus an
   envelope evidence entry. Influence without citation is not
   influence; the spec on disk is the proof.
3. **The bundle records the loop**: `memory.recalled_lessons` and
   `memory.applied_to_spec` on every bundle; the front door prints
   both ("memory: N lesson(s) recalled; M cited in the spec").
4. **Scope, disclosed**: graph plans recall into context the same
   way, but only the reference plan has an architect node to cite —
   an operator's graph names its own planner. The foreman's
   repairs still do not feed the planner (named, open).

## What this does NOT claim

Under the EchoModel, "applying a lesson" means it reaches the
plan's context and is cited in the spec — structural influence.
A lesson changing executor BEHAVIOR requires a model that can act
on what it reads: First Light (ADR-054 Phase C, operator opt-in).
The test suite pins the structural loop and the disclosure.

## Consequences

- Two runs in one workspace demonstrably compound: the second run
  recalls the first run's `proven::*` records (evidence-validated
  lessons that did not exist at the first run's recall time) and
  cites them in its spec.
- Fresh workspaces recall the disclosed prior-run seeds — the
  bundle reports what was recalled, honestly labeled by source.
- Spine step 9 moves from PARTIAL to closed-for-the-pipeline
  (~39% → ~53% end-to-end with v39.8.0's steps 2 and 7; method:
  conservative step-level scoring in docs/STATE-OF-AEOS.md).
