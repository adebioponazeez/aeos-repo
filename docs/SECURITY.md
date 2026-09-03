# Security — AEOS v1.0.0

## Threat model (who can hurt us)

1. **A confused or injected agent** tries to write where it shouldn't,
   or claims work it didn't do. → *Boundary enforcement + gates.*
2. **A looping agent** burns resources on retries. → *max_attempts + repair
   budget per run; every attempt is an event.*
3. **An over-permissioned graph** lets two writers race. → *Graph validation
   rejects unordered overlapping writers before anything runs.*
4. **Stale/poisoned knowledge** degrades future runs. → *Freshness expiry,
   confidence floors, evidence-gated canonical writes.*
5. **A prompt-injected tool result** escalating privileges. → *Action
   classes are task-declared and governor-checked per execution, not
   session-global; unknown classes fail closed.*

## The permission model, precisely

Every task declares an `ActionClass`. The governor maps
`(action_class, current_autonomy_level)` to ALLOW / CHECKPOINT / DENY
using a data table (`governor.py::_DEFAULT_POLICY`) — auditable in one
screen, overridable only by editing code with review.

- READ ≥ L1 → ALLOW.
- WRITE/EXECUTE ≥ L3 → ALLOW; below → CHECKPOINT.
- NETWORK/DEPLOY ≥ L4.
- FINANCIAL / DESTRUCTIVE / CREDENTIAL: CHECKPOINT at *every*
  occurrence even at L6 — promotion does not create blank checks.
- IRREVERSIBLE: DENY below L7 + explicit human sponsorship.
- **Unknown class: DENY.** Fail closed, always.

Write boundaries (`writes:` globs per agent) are enforced *after* every
agent call by full-workspace diff against a pre-call checkpoint;
unauthorized creations and modifications are reverted and the phase
dies. `.aeos/` (OS state) is inside the fence by design — the system's
own bookkeeping is never an agent's to edit.

## Secrets

v1.0 ships no credential plumbing on purpose: the deterministic runtime
needs none, and `CREDENTIAL` is a checkpoint-forever action class.
Production adapters inject keys via environment at the adapter seam —
never into agent context, never into the event log (events serialize
`default=str`; the EventLog does not redact because nothing secret
should ever be passed to it — enforced by convention + review, flagged
as a v2 hardening item in ADR-008).

## Audit

`EventLog` is append-only JSONL: every decision, gate, transition, and
violation lands with a timestamp. `harness.violations` records every
reverted write with the agent responsible. Runs end with an evidence
bundle (`evidence/bundle.json`) that answers "what happened, and what
proved it" without replaying anything.
