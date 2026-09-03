# ADR-003: Typed envelopes + evidence gates at every boundary

**Status: ACCEPTED (v0.2), hardened (v1.0)**

## Context
Free-text agent output cannot be verified, scheduled, or repaired.
SSSF proved the pattern (typed envelopes; `gate(envelope, run) ->
violations`); we generalize it graph-wide and add the
anti-hallucination gate.

## Decision
Every handler returns
`Envelope{claims, evidence, artifacts, changed_files}`. Stock gates:
`artifacts_exist`, `artifacts_non_empty`, `json_artifacts_parse`,
`changed_files_exist`, and **`claims_are_backed`** — a claim set with
zero PASS evidence fails the envelope. Verdicts come from the closed
set PASS / FAIL / PARTIAL / UNVERIFIED; a report with no checks stays
UNVERIFIED, because absence of failure is not success.

## Alternatives considered
- **LLM-as-judge as primary gate** — rejected: judges can be argued
  out of facts; `artifacts_exist` cannot.

## Tradeoffs
(+) Hallucinated success becomes mechanically impossible to ship.
(−) Gates are shallow (existence, shape, consistency); semantic review
still requires an evaluator agent or a human. The seam is `Gate`, not
a promise.

## Consequences
The end-to-end run is accepted only when artifacts exist on disk,
parse cleanly, and claims carry evidence — all checked by code.
