# ADR-013: Sponsorship — human authority as a spendable token

**Status: ACCEPTED (v3.0)**

## Context
L6/L7 actions (installing capabilities, changing the system itself)
need human authority that is stronger than "yes" and weaker than
"admin": approval fatigue creates rubber-stamps; global admin creates
blank checks.

## Decision
`SponsorshipGate` issues tokens that are **scoped** (one named
action), **one-shot** (spending is atomic; replay refused), **expiring**
(default one hour), and **audited** (every issue/spend/refusal
recorded with outcome). Factory installs and meta-loop changes
require one; there is no bypass path in code.

## Alternatives
- The governor's one-shot approvals: too weak — they authorize a task,
  not a *change to the system*.
- Static allowlists: not expiring, not auditable per-use.

## Tradeoffs
(+) "Who authorized this capability?" is answerable from the audit.
(−) Token plumbing is manual in v7 — a UI/console is v8 work.

## Consequences
Demonstrated in the v7 evidence: without token, 2 proposals / 0
installs; with a scoped token, exactly the scoped install — the
second candidate refused on scope mismatch.
