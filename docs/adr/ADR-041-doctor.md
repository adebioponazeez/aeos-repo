# ADR-041: Claims become checks

**Status: ACCEPTED (v32.0)**

## Context
The charter's oldest claim — zero runtime dependencies (ADR-002) —
was verified by inspection for 31 versions. So were workspace and
repo health. Inspection rots; checks do not.

## Decision
`doctor.py` — the system audits itself: (1) `zero_dep_audit()` parses
every module's imports (ast) and classifies stdlib / aeos / VIOLATION
— a non-stdlib import anywhere fails the command; (2) workspace
health: schema versions (current/legacy/FUTURE=FAIL), torn sidecars
(WARN), stale-vs-held locks (the kernel-release law), disk, retention
hint; (3) repo health: clean tree, tags. Verdicts PASS/WARN/FAIL with
named detail; FAIL exits nonzero — a doctor that flatters is not a
doctor. Building it caught two of its own bugs immediately (relative
imports misread as violations; repo root mislocated) — the check
checked itself before it checked the system.

## Consequences
`test_the_charter_claim_is_machine_checked`,
`test_violations_are_named`, `test_future_schema_fails`,
`test_doctor_command_exits_by_health`.
