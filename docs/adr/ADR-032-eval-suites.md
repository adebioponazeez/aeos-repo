# ADR-032: Runs are graded, not watched

**Status: ACCEPTED (v23.0)**

## Context
BENCHMARK-2026 named offline eval suites as our gap: Mastra and
LangSmith grade runs; we only gated them at runtime.

## Decision
`EvalSuite` — cases with deterministic judge PREDICATES (no model
grades itself), weights, and a pass threshold. A case that raises
FAILS with the exception name, never crashes the suite; scores clamp
to [0,1]. `run_self_eval` points the mirror at AEOS's own six laws
(standards gate, recall budget, negative marginal, UNTRUSTED
imports, phantom detection, byte-stable prefixes) on real fixtures.

## Alternatives
LLM-as-judge: rejected — an evaluator that can be charmed is not an
evaluator (the v18 law, restated).

## Consequences
`test_weights_shape_the_score`, `test_raising_case_fails_without_crashing`,
`test_aeos_grades_its_own_laws`.
