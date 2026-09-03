# ADR-026: Plans survive their process

**Status: ACCEPTED (v17.0)**

## Context
AFK agents that restart from zero on crash were never AFK. Durable
execution is the industry's headline feature (LangGraph checkpoints,
Pydantic AI via Temporal) and our honesty gap: waves died with the
process.

## Decision
`PlanCheckpoint` — atomic (tmp-then-rename) JSON checkpoint written
after EVERY completed task. `execute_plan` — executes only pending
tasks, raises `ResumeNeeded` on failure with progress durable,
resumes across processes with side effects exactly once (the call log
is the idempotency proof). No daemon, no broker: a file.

## Alternatives
Temporal/DBOS-class durable runtimes: rejected as default — heavy
dependency for single-host plans; the checkpoint schema is portable
to them later.

## Consequences
`test_crash_midplan_keeps_prior_progress`,
`test_side_effects_happen_exactly_once`,
`test_progress_survives_a_new_process`.
