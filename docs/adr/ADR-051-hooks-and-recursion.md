# ADR-051: Hooks as a first-class surface; harnesses nested as graphs

**Status: ACCEPTED (v39.5.0)**

## Context

Two references, one question. Cole Medin's advocacy (long-running
agents, his knowledge base): the bash-command hook as guardrail is
not an add-on — hooks are THE critical mechanism; a harness is
prompts plus files, the agent is swappable, and the guardrails live
in the hook layer. And the Recursive Agent Harness pattern
(arXiv:2606.13643): the recursive unit is a full agent harness —
filesystem tools, execution, planning — not a model call; a parent
spawns subagent harnesses and gains ~10 points of long-context
task success over the flat baseline, attributable to the harness
rather than the model.

AEOS before this ADR had the SEMANTICS scattered but no surface:
the governor is an access + pre-execution hook; `attach_persistence`
is a monkey-patch hook; CHECKPOINT is redirect-not-reject. And the
graph scaffolds were flat: orchestrator waves and colony DAGs, but
a task could never expand into a sub-harness.

## Decision

1. **A first-class hook bus** (`hooks.py`). Closed vocabulary of
   named points on the harness scaffold — task.pre/post,
   wave.pre/post, subplan.pre, refusal. Registrations are ordered,
   thread-safe, inspectable (`aeos hooks`), decoupled from the
   agent (infrastructure-level: consistent regardless of model).
   Pre-hooks may VETO (HookVeto — the message IS the reason the
   operator sees, plain language, never a traceback) or REDIRECT
   (rewrite the action class, e.g. WRITE→READ: intent preserved,
   danger removed). Observers run after; an observer exception is
   collected and named — an observer can never crash the run it
   observes.
2. **Recursive harness graphs.** `TaskSpec.subplan`: a task with a
   subplan expands into a NESTED Orchestrator with its own waves,
   governor decisions, gates and events (subplan.start/end,
   depth-stamped), sharing the log, hooks and evaluator. The
   parent settles from the child's report; a child failure fails
   the parent NAMED ("subplan unresolved: [tasks]").
3. **Recursion is depth-capped at 3.** Deeper nesting refuses
   NAMED — "recursion is a tool, not a trap" — and the refusal
   flows to the refusal hooks like every other refusal. This is a
   recursive STATE MACHINE in the honest sense: a state (task)
   that expands into a sub-state-machine, bounded, observed, and
   reversible at every level by the existing checkpoint law.

## Honest scope

- Hooks are in-process Python callables inside the OS trust
  boundary: guardrails against AGENT behavior, not a plugin
  sandbox against hostile code. A hostile hook is inside the wall
  already; sandboxing plugins is a different (and future) ADR.
- Subplans are runtime constructs. Durable checkpoints store the
  parent's settled state; the child re-derives on resume —
  lawful only because handlers are idempotent (spec §14).
- The wave.pre point is observer-only: redirecting a wave mid-loop
  would violate the parallel-boundary law; veto belongs to
  task.pre, where the boundary is per-task.

## Consequences

- The kernel stays readable (ADR-002): hooks emit from existing
  seams; no logic moved into the bus.
- The reference pipeline runs green with hooks emitting end-to-end
  (tested) — the surface composes WITH the kernel, not against it.
- The dark-factory pattern map gains its Cole Medin row and its
  recursive-harness row; the flat-graph limitation is closed.
