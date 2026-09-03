# ADR-028: Standards are cited, not remembered

**Status: ACCEPTED (v19.0)**

## Context
"Success is planned": the 80-20 of agentic coding is encoding
engineering standards BEFORE the build. Our memory arc learns
standards after the fact — necessary, not sufficient.

## Decision
STANDARDS.md registers operator law as `[STD-n]` ids. The plan gate:
if standards are registered, a plan citing none is REFUSED; a
citation that is not registered is REFUSED. No file, no gate —
standards are the operator's choice, never imposed. Enforced at the
top of the reference pipeline, before any work happens.

## Alternatives
LLM-judged plan quality: rejected — the gate must be deterministic
and offline. Baking standards into prompts: rejected — unciteable,
unauditable.

## Consequences
`test_plan_without_citation_is_refused`,
`test_uncited_intent_fails_when_standards_registered`,
`test_unregistered_citation_is_refused`.
