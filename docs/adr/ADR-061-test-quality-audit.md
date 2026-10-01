# ADR-061: The test suite must bite — mutation sensitivity as law

**Status: ACCEPTED (v40.4.0)**

## Context

The Reckoning's register: "test-count theater risk — 620 tests
sounds like proof; a large fraction might pin demo-path behavior."
Test counts measure existence, not sensitivity. This audit measured
sensitivity mechanically (docs/TEST-AUDIT.md): four one-line
mutations neutered load-bearing product laws and the full suite
counted failures.

## Findings

- Classification (AST, 53 files): 73% product-surface, 24%
  kernel-law, 2% demo; 68 refusal tests; **0 vacuous**.
- Mutations: gates-off → 69 failures; autonomy-off → 11;
  boundary-wiring-off → **0 (a real hole)**; redaction-off → 2.
- The hole: `harness.enforce_boundary` was tested at the mechanism
  level, but the reference pipeline's `bounded()` wrapper was not —
  the exact "tested mechanism, untested wiring" family the Spine
  exposed in product code.

## Decision

1. **Mutation-mirroring tests are law for wiring-level behavior.**
   Fixed in this release: the boundary wiring pin (rogue-contract
   roster through the REAL pipeline → violation named, write
   reverted, run refused — with an honest control that the real
   roster still succeeds) and the redaction pin at the bus surface.
2. **The sweep is documented, not automated in CI**: mutating main
   on every push is slow and noisy. The four mutations live in
   docs/TEST-AUDIT.md as a manual protocol, re-run when the wiring
   surfaces change.
3. **Counts stay secondary**: the README's test count remains, but
   the proof-of-quality citation is the audit doc, not the number.

## Consequences

- 3 new tests (620 → 623); the M3 hole cannot silently regress.
- Future ADRs that add wiring-level laws should name their
  mutation-mirroring test (the M3 pattern).
