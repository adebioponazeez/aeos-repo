# ADR-048: The Foreman — the autonomous operator

**Status: ACCEPTED (v39.0.0)**

## Context

The operator's direction: "all the above is for you to actually use
it to produce a compelling production-grade autonomous agentic AI
software system — and not a PDF — following the tradition of dhh,
creator of Omarchy." The Omarchy lesson: a powerful-but-fiddly
foundation (Arch; here, 36 verbs of harness) becomes a product when
someone ships the curated, opinionated, one-command experience on
top. AEOS had every muscle — audits, groom, backup drills, the
notary, the boot ledger — and no agent that used them.

## Decision

`foreman.py` + `aeos foreman [--apply]`: an autonomous agent whose
entire behavior is the loop the charter has been building since v1:

1. **PERCEIVE** — survey the workspace: state schema, torn writes,
   run retention, backup posture, boot-ledger outcome, machine
   outbox, and (in a checkout) README drift and save-proof ledger
   verification. Findings are facts with remedies.
2. **PLAN** — classify honestly: MECHANICAL (safe, deterministic,
   reversible: upgrade, archive, groom, drill) or PROPOSAL (human
   craft: documentation, dead letters, investigation). Proposals
   are filed with a "what to do" and are never silently attempted.
3. **ACT** — only with `--apply`, only the mechanical class, in
   fixed dependency order (schema → torn → groom → backup-drill:
   heal first, then capture the healed state). Safe by default:
   survey is the mode. A failing action stops the run — the
   foreman never continues past a broken step.
4. **VERIFY** — re-survey; a finding that survives its own remedy
   is named. Every receipt carries pre/post Merkle roots of the
   workspace: what the agent did to your state is cryptographically
   visible.
5. **REMEMBER** — append-only, signature-deduped history; recurring
   findings are a pattern, not a surprise. No clocks in artifacts
   (determinism law): sequence numbers are time.

Boundaries: writes only inside the workspace; every write atomic or
append-fsynced; exit codes are a contract (0 clean/resolved · 1
attention · 2 failed); receipts carry no secrets. Convention over
configuration: KEEP_RUNS=10, no knobs.

**No printing this release.** The operator asked for the system,
not the shelf: no book chapter, no PDF assets. The product is the
code and its receipts.

## Consequences

The doctor gains a "foreman ledger" row (last run: mode, resolved,
remaining). Charter principle 41: the shop runs itself between
visits. The agent's remediation class will grow only by ADR — each
addition must be safe, deterministic, reversible, and verified by
re-measurement. Dogfooded on landing: a degraded workspace healed
end-to-end (4/4 mechanical resolved, second pass quiet), and the
one proposal it filed (README drift) was real and fixed the same
hour.

## Tests

`test_degraded_workspace_finds_all_four_mechanical`, `test_fixed_order_and_heal_before_backup`,
`test_apply_resolves_every_mechanical_finding`, `test_backup_drill_verifies_the_restore`,
`test_idempotent_second_run_changes_nothing`, `test_failure_stops_the_run_with_exit_2`,
`test_proposals_are_never_executed`, `test_history_dedupes_by_signature`,
`test_survey_is_deterministic`, `test_receipts_carry_no_secrets`.
