# ADR-046: The Ignition — one front door, plain-language failure

**Status: ACCEPTED (v37.0.0)**

## Context

Operator feedback after v36, paraphrased faithfully: the system had
grown 35+ verbs and offered no single production entry point — no
"just run it" — and when a real environment fails to load up
(permissions, full disk, state written by a newer build, a missing
provider key, a crashed previous run), a stack trace is not help.
Production engines are judged at boot, in the dark, by someone in a
hurry who did not write the code.

## Decision

`ignition.py` + `aeos up` — an init system, not another feature:

1. **Four stages, always in order**: PREFLIGHT (power-on self-test:
   python version, disk, the ADR-002 zero-dep scan, workspace
   writability, state schema from the future, torn sidecars, lock
   holders, live-key presence, previous-boot outcome) → WORKSPACE
   (create, heal, in-place schema upgrade via groom) → WORK (the
   reference loop with its evidence bundle) → SHUTDOWN (a numbered,
   atomically-written boot receipt in `.aeos/boots/`).
2. **Exit codes scripts can branch on**: 0 ok · 2 preflight ·
   3 workspace · 4 work · 5 shutdown.
3. **The plain-language law**: every FAIL carries WHAT HAPPENED and
   WHAT TO DO, one breath each. Never a traceback. Structurally
   enforced: `Check.remedy` is required for FAIL
   (`test_every_fail_carries_a_remedy`).
4. **The boot ledger**: every boot — including failed ones — writes
   a receipt; the next boot's preflight reports how the last one
   ended, with the reassurance that atomic writes mean no torn
   state. The system's history explains its own crashes.
5. **First-cause preservation**: a shutdown failure (receipt cannot
   be written) is appended to the result; it can never overwrite the
   original failure that caused it. The first failure is the truth.
6. **No secrets in receipts**: key PRESENCE is checked, key VALUES
   are never read into any receipt or render.
7. **Nested-proof guard** (found the hard way — twice): `aeos up
   --save-proof` inside a test run spawned the test suite inside the
   test suite — a proof containing itself. Proof commands now run
   with `AEOS_PROOF_INNER` set, and a notary asked for the DEFAULT
   SUITE COMMAND that sees it refuses: one proof at a time. The
   first guard was too blunt (it refused honest certificate
   construction with explicit commands, and the notary proved it by
   refusing this release's own first proof — outcome TESTS-FAILED,
   certificate kept in the ledger as history); the sharpened guard
   targets only the real recursion vector: the suite itself.
8. Doctor gains a "boot preflight" row for workspace contexts:
   which checks would block `aeos up` right now.

Existing verbs are unchanged — capabilities are permanent (v36
law); `aeos up` is the door, not a demolition.

## Consequences

One module, one verb, 19 tests. The README's quick start now begins
with `aeos up`. Charter principle 39: the door is one, and failure
speaks plain language. The recursion defect is recorded here and in
the CHANGELOG because a defect found by your own test suite and
fixed with a guard is documentation, not embarrassment.

## Tests

`test_healthy_workspace_is_all_clear`, `test_state_from_the_future_fails_with_remedy`,
`test_every_fail_carries_a_remedy`, `test_live_without_key_names_the_env_vars`,
`test_live_with_key_never_reads_the_value`, `test_unwritable_workspace_fails_with_permissions_remedy`,
`test_preflight_is_deterministic`, `test_happy_path_four_stages_and_receipt`,
`test_boot_ledger_grows_and_remember`, `test_preflight_failure_exits_2_and_speaks`,
`test_work_failure_is_named_not_traced`, `test_next_boot_reports_the_previous_crash`,
`test_workspace_failure_path_exits_3`, `test_receipt_carries_no_secrets`,
`test_save_proof_without_checkout_is_an_honest_skip`, `test_nested_proof_is_refused_not_recursive`,
`test_doctor_reports_boot_blockers`, `test_failure_render_names_stage_and_remedy`.
