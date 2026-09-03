# ADR-037: State declares its version; storage pays its keep

**Status: ACCEPTED (v28.0)**

## Context
Two deployment-review findings: long-lived state (memory, fleet
stream, checkpoints) carried no format version — an upgrade had no
migration path and no way to refuse future formats; and `.aeos/runs/`
grew without bound — no retention story.

## Decision
**Schema law:** long-lived state opens with an `{"aeos_schema": 1}`
header. Legacy (v27-era) files without a header load as schema 1
(back-compat, no rewrite). State written by a NEWER aeos fails
closed with `SchemaError` — never guess, never partially load.
**Retention:** `aeos groom` upgrades legacy state in place (atomic
writes) and archives all but the newest N run event files to
`.aeos/archive/runs/` — nothing is ever deleted; archived,
retrievable, auditable. The receipt names everything it did.

## Alternatives
Deleting old runs to "free space": rejected — evidence is never
destroyed, only shelved. Auto-groom on every run: rejected —
retention is an operator decision, scheduled, not ambient.

## Consequences
`test_future_schema_fails_closed`, `test_legacy_v27_file_still_loads`,
`test_groom_upgrades_archives_receipts`, `test_groom_is_idempotent`.
