# ADR-044: Documentation cannot drift

**Status: ACCEPTED (v35.0)**

## Context
Every version hand-bumps counts in six documents; hands drift. The
v35 build found FOUR stale live claims in the README on its first
run — including two v1/v11-era numbers ("131 tests", "177 tests")
nobody knew were still there. Docs lie quietly; receipts do not.

## Decision
`scribe.py` + `aeos scribe`: extracts verifiable claims from the
living docs — test/proof counts, module counts, ADR counts, the
version headline, every `aeos <command>` mentioned — and checks each
against LIVE reality (imported version, counted tests, globbed
modules/ADRs, parsed CLI). Drift FAILs with file:line. Exemptions,
by design: version-table rows and the historical record
(CHANGELOG/ADR/book count at tag time) — history is not a claim
about the present. "N+" lower-bound forms pass while N <= actual.
The doctor carries a "README tells the truth" row (checkouts only);
the charter gains principle 37. Dogfooded on landing: the scribe's
first receipt was the four real drifts, fixed in the same commit.

## Consequences
`test_the_real_readme_is_truthful_today`, `test_drifted_readme_fails_with_location`,
`test_version_table_rows_are_history`.
