# ADR-038: Backups are drilled, not assumed

**Status: ACCEPTED (v29.0)**

## Context
F-09: atomic writes protect against crashes, not against deletion —
`.aeos` state had no backup/restore proof. F-08: stability was
asserted from single runs, never from sustained operation.

## Decision
**Backup law:** a backup is a DETERMINISTIC tar — sorted members,
fixed metadata, and a manifest carrying ONLY what verification needs
(no clocks, no paths): identical state yields byte-identical
archives, provable by hash. The manifest maps every member to its
sha256; restore verifies EVERY member before touching the workspace
and REFUSES entirely on any mismatch (a corrupt backup restores
nothing, never something wrong). Caches are never carried — the
recall index is rebuilt on restore, proving it is a cache. Locks are
never carried — a restored lock would be stale by definition.
**Soak law:** `aeos soak` is sustained operation as a receipt — N
consecutive runs on one workspace, state accumulating, with
wall-clock mean/max, token/cost totals, memory growth, disk delta.
Live soak is opt-in only (AEOS_LIVE=1 + provider key) under a hard
dollar cap. The backup→destroy→restore→re-run drill is a permanent
storm scenario (9/9).

## Alternatives
Copying the directory: rejected — no verification, no determinism,
carries locks and caches. Snapshotting to cloud: refused as default —
network-optional system.

## Consequences
`test_tampered_backup_refused_fail_closed`, `test_backup_is_deterministic`,
`test_backup_restore_drill_in_the_storm`, `test_live_soak_requires_opt_in`.
