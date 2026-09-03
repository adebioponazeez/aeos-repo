# ADR-042: The charter is load-bearing — machine-checked

**Status: ACCEPTED (v33.0)**

## Context
PRINCIPLES.md cites a test name for every compiled value — a claim
that decays silently the day a cited test is renamed or removed.
And the schema law (ADR-037) was proven unit-wise, never end-to-end
across real version distance.

## Decision
**Charter check:** `doctor.charter_check()` parses every
`test_*` token cited in PRINCIPLES.md and verifies each exists in
the suite corpus; a cited-but-absent test FAILS the doctor (the
constitution cannot reference phantom laws). Shipped as a doctor row:
"charter is load-bearing — 34 cited test(s) all exist."
**Upgrade drill (end-to-end):** a genuine v27-era workspace (header-
less memory/events/checkpoint, 12 run files) must LOAD back-compat,
GROOM to current schemas in place, ACCEPT a fresh run, pass doctor
with zero failures, and survive a backup/destroy/restore roundtrip —
one test spanning six versions of state evolution. Future-schema
state still fails closed end-to-end.
**Publishing last mile:** `.github/workflows/release.yml` — tag-
triggered prove→build→twine-check→publish via PyPI trusted
publishing (OIDC, no long-lived tokens), INERT until the operator
sets the `PYPI_ENABLED` variable and wires the pending publisher
(docs/PUBLISHING.md, three steps).

## Consequences
`test_charter_is_load_bearing`, `test_missing_cited_test_fails`,
`test_v27_state_serves_at_v33`, `test_healed_workspace_backs_up_and_restores`.
