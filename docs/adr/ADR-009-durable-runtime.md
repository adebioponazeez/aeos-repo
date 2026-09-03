# ADR-009: Durable runtime — persist at transitions, resume without rework

**Status: ACCEPTED (v2.0)**

## Context
Long-running agent fleets die: processes crash, machines recycle,
deployments restart. A run that must restart from zero after a crash
taxes every long objective.

## Decision
Persist a minimal `RunState` (task specs + states + attempts) after
every task transition, write-then-rename for crash atomicity.
`resume_plan` keeps SUCCEEDED tasks (their artifacts are already on
disk — the filesystem is the working memory, ADR-006) and re-runs only
what is unfinished. Handlers are addressed by agent name from the
registry, so a resumed run in a new process re-binds behavior.

## Alternatives
- Full event-sourced replay: rejected for v2 — replaying handlers is
  only sound with deterministic models; state checkpoints are honest
  about the seam.
- External workflow engine: rejected — adds a dependency and a
  second source of truth (ADR-002).

## Tradeoffs
(+) Crash becomes a pause, not a loss.
(−) Envelope payloads are not persisted (states only) — evaluations
re-run on resume; acceptable because gates are cheap and idempotent.

## Consequences
Proven by `test_failed_run_is_resumable_and_then_completes` and
`test_succeeded_tasks_are_not_rerun`.
