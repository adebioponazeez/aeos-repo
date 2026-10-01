# TEST-QUALITY AUDIT — does the suite bite? (at v40.4.0)

*The Reckoning's register named the risk: "test-count theater —
620 tests sounds like proof; a large fraction might pin demo-path
behavior, not product behavior." This audit answers with two
mechanical measurements, not narrative: a per-test classification
of what the suite actually exercises, and a mutation sweep — real
product laws neutered one line at a time, full suite, failures
counted.*

---

## 1. What the suite actually tests (AST classification, 53 files)

Every test file was parsed; each test's calls were resolved through
its imports and classified by the surface they reach. File-level
granularity, disclosed:

| Class | Files | Tests | Share |
|---|---|---|---|
| **Product-surface** (cli/pipeline/foreman/boot/doctor/scribe/groom/backup/stream/graphlang/storm/holdout/vault/saveproof/outbox/resume/bench) | 39 | 453 | 73% |
| **Kernel-law** (contracts, governor, memory, evaluation, providers, distance...) | 13 | 151 | 24% |
| **Demo-surface** (factory/federation/colony/companions demos) | 1 | 14 | 2% |

- **Refusal tests** (`pytest.raises` on a named refusal): **68** — the
  refusal vocabulary is heavily pinned.
- **Truly vacuous tests** (no assert, no raises, no output check):
  **0.** The suite is not inflated with empty tests.

The theater fear is inverted at the file level: demos are 2% of the
suite. But classification cannot see whether the tests would CATCH
a regression — for that, mutations.

## 2. The mutation sweep (the suite must bite)

Four one-line mutations, each neutering a load-bearing product law;
after each, the FULL suite ran and failures were counted; each
mutation was then reverted (git checkout, verified clean):

| # | Mutation (one line) | Law neutered | Failures |
|---|---|---|---|
| M1 | `for gate in self.gates:` → `for gate in []:` (evaluation.py) | evidence gates never run | **69** |
| M2 | force `min_level=L0, deny_by_default=False` (governor.py) | autonomy ladder open to all | **11** |
| M3 | `reverted = harness.enforce_boundary(...)` → `reverted = None` (pipeline.py `bounded()`) | write-boundary not enforced | **0 — HOLE** |
| M4 | `redact()` returns detail unchanged (observability.py) | secrets leak into events | **2 — thin** |

## 3. Findings and fixes (this release)

1. **M3 was a real hole, now fixed, pinned AND re-proven.** The
   boundary law (invariant #2: "no authority without a boundary")
   was tested at the MECHANISM level (`harness.enforce_boundary`,
   test_harness.py) and in the companions' wiring — but not through
   the reference pipeline's `bounded()` wrapper. Disconnecting the
   wrapper would have shipped silently. Pinned by
   `test_v404_testaudit.py::test_m3_the_pipelines_boundary_wiring_bites`
   (a rogue-contract roster drives the REAL wiring: violation named
   on the event log, write reverted, run refused) plus an honest
   control (the real roster's legitimate build still succeeds).
   **Post-fix re-sweep (captured): M3 re-applied to the pinned tree
   → the full suite fails with exactly 1 failure — the pin itself
   (0 → 1; the hole is closed, proven, not assumed).**
2. **M4 was thin (2), now thickened.** Redaction is additionally
   pinned at the BUS surface — the file the shopfloor streams must
   never carry a secret (`test_m4_secret_redaction_pinned_through_
   the_bus`).
3. **M2 (11 failures) is acceptable and named**: the ladder is
   pinned by the governor/policy/escalation tests; most of the
   suite runs at L5 where the mutation changes nothing.
4. **M1 (69 failures)**: the evidence-gate law is deeply pinned.

## 4. The honest verdict on "test-count theater"

**Not empty tests — untested wiring.** The suite has zero vacuous
tests and demo-path coverage is 2%. The real theater risk is the
one the Spine already exposed in product code: a mechanism can be
thoroughly tested while its COMPOSITION into the product path is
not (M3 is exactly this family). The count is not the proof; the
bite is.

## 5. Protocol going forward

- The four mutations above are a documented sweep (this file) —
  re-run manually when the wiring surfaces change (pipeline bounded,
  event redaction, evaluator gates, governor policy). A CI mutation
  job was considered and rejected: mutating main on every push is
  slow and noisy; the sweep is a scalpel, not a heartbeat.
- New wiring-level laws should ship with a mutation-mirroring test
  in the same PR (the M3 pattern: sabotage the contract, demand the
  refusal).
