# ADR-055: The Spine — one execution path for every plan

**Status: ACCEPTED (v39.8.0)**

## Context

The audit (ADR-054, docs/STATE-OF-AEOS.md) scored the disjointedness:
`aeos graph --run` executed compiled DOT on a DEMO roster whose
handlers fabricated PASS evidence, while the reference pipeline ran
its own hardcoded 7 tasks. Two planners, two wirings, zero
composition — and worse, the demo path had drifted into holding
product responsibilities (it was the only way to "run a graph").

Digging deeper during implementation exposed a third defect of the
same family: the reference builder handler branched on the literal
task name `build-core`, so ANY other builder task silently fell
into the CLI branch and built the wrong artifact — a silent
mis-build waiting for the first operator graph.

## Decision

1. **One execution path.** `reference_run` accepts a compiled
   `tasks` list (graphlang output or any conforming plan). An
   operator's graph and the reference objective run through the
   SAME pipeline: same roster, same handlers, same evidence law,
   same bundle, same learning loop. The demo roster is retired from
   graph execution (`_demo_orchestrator` survives only for the
   hooks demo, which demonstrates hooks).
2. **`aeos run` is the spine's front door**: the reference
   objective by default, `--graph plan.dot` for an operator's
   workflow; `graph --run` delegates to the same code.
3. **Contract law at the spine's door.** Before any work: every
   graph task's agent must BE a registered contract, and every
   task's action class must lie inside that contract's
   `action_classes`. Unknown agent or class → named refusal with
   the roster and the remedy. (This closes the hole the example
   graph itself had: a WRITE task assigned to the READ-only
   executive — it only ever "worked" under the permissive demo
   roster.)
4. **Capability dispatch, not name coupling.** The builder handler
   dispatches on a capability namespace (`core`, `cli`), tolerant
   of a `build-` prefix; unknown capabilities REFUSE with the list
   of what the builder can build — never a silent mis-build.
5. **One event bus.** With `live_events=True` the pipeline streams
   its event log to `<ws>/.aeos/runs/<ts>-events.jsonl` WHILE the
   run happens — the same file the shopfloor tails. Pipeline runs
   and graph runs are indistinguishable to the viewer.
6. **Nested harnesses count.** Learning, discovery and the evidence
   bundle walk into subplans (`_walk_tasks`): the graph's nested
   harnesses produce lessons and bundle rows like any other task.
7. **Self-describing bundles.** Every bundle states its
   `plan_origin` (reference | operator-graph) and whether events
   were live.

## Consequences

- The spine matrix step 2 (intent → plan) and step 7 (operator
  watches live) move to WORKS; end-to-end completeness ~39% → ~50%
  (re-scored in docs/STATE-OF-AEOS.md).
- The example graph was corrected to name real contracts
  (`release` work belongs to the `release` agent).
- `run-demo` remains as the legacy reference-run surface; the Front
  Door Diet (Phase D) will consolidate.
- What the spine does NOT yet do: execute a real model (First
  Light, operator opt-in), or feed the foreman's lessons into the
  next plan (closing the loop). Both remain named gaps.
