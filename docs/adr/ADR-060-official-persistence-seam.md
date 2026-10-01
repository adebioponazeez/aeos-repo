# ADR-060: The official persistence seam — no more monkey-patching

**Status: ACCEPTED (v40.3.0)**

## Context

The audit's register of structural debt: "persistence via
monkey-patch (runtime.py)". `attach_persistence` wrapped the
orchestrator's private `_execute_task` from outside — invisible to
type checkers, fragile against signature drift, and semantically
narrow: it ran only when the method returned normally, so a raise
that blew past the handlers (an interrupt) recorded nothing.

## Decision

1. **The orchestrator owns the seam.** `Orchestrator.__init__`
   takes `on_task_settled: Callable[[TaskSpec], None] | None`;
   `_execute_task` is now a settle wrapper that calls the seam in a
   `finally` after `_execute_task_inner` — every transition path
   (success, failure, escalation, governor denial, hook veto,
   subplan parent) settles the seam, and an interrupt that escapes
   the handlers still records the attempt.
2. **Nested harnesses inherit the seam.** `_run_subplan`'s child
   orchestrator is constructed with the parent's `on_task_settled`
   — nested harnesses count (the same law as v39.8's learning
   walk). This gap was caught by this ADR's own tests before
   shipping: the first draft left children unseamed.
3. **`attach_persistence` keeps its signature** (public API; the
   resume tests import it) but now sets the public seam — no
   instance-dict wrapping, no private reach-through. Pinned by
   test: `"_execute_task" not in orch.__dict__`.
4. **Failure stays loud.** A seam that raises propagates as before
   — a refused persistence write is a run-level event, not
   something to swallow silently.

## Consequences

- `resume`'s durable plans are unchanged in behavior (the
  test_platform resume suite passes untouched) and stronger in one
  case: interrupts now record the attempt.
- The audit's register closes another line; what remains from the
  structural-debt register: the colony engine (bench-wired; its own
  retirement ADR when taken) and the wording pins (accepted as a
  cost of pinned user-facing contracts, documented).
- The hooks docstring no longer describes persistence as a
  monkey-patch hook.
