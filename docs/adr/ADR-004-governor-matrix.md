# ADR-004: Autonomy governor — a data table that fails closed

**Status: ACCEPTED (v0.3)**

## Context
Spec §§19 and 25: classify every action; ladder autonomy L0–L7;
increase autonomy only with evidence. Most agent incidents trace to
over-broad permissions or to approval fatigue (humans trained to click
yes).

## Decision
One table maps each `ActionClass` to (minimum autonomy to allow,
deny-by-default). `decide()` returns exactly ALLOW / CHECKPOINT /
DENY. Unknown action classes DENY — fail closed, always.
FINANCIAL / DESTRUCTIVE / CREDENTIAL checkpoint at EVERY occurrence
even at L6: autonomy is earned per class, not granted globally. The
level tracks a reliability EMA (gain 0.3): sustained success promotes,
failures demote — automatically, in the event log.

## Alternatives considered
- **Static per-agent permissions** — too coarse; misses task-level
  action classes.
- **Human approval for everything** — approval fatigue defeats it; the
  ladder exists precisely so routine classes stop asking.

## Tradeoffs
(+) The whole security posture is one auditable screen of data.
(+) Demotion is automatic: a bad night costs the fleet its privileges.
(−) Conservative defaults checkpoint often early on (by design).

## Consequences
The reference run earns L5 from observed reliability 1.0 across seven
tasks. Promotion is in the log, not in the marketing.
