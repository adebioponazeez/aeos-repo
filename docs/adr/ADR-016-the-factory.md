# ADR-016: The Capability Factory — L7 as a bounded pipeline

**Status: ACCEPTED (v7.0)**

## Context
The spec's terminal object: "systems that discover what systems
should exist." The failure mode is a system that promotes capabilities
on enthusiasm — the folklore problem at architectural scale.

## Decision
The factory is a five-stage pipeline, each stage emitting evidence:
**measure** (discovery signatures) → **design** (a conservative
contract template derived from the signature: the action class
determines the write boundary) → **sandbox-validate** (the contract
must pass spec validation AND a smoke task under the real harness +
gates on the deterministic engine) → **propose** → **install**
(sponsorship token, scoped and one-shot, ADR-013). A candidate whose
sandbox verdict is anything but PASS cannot reach the install branch —
there is no override.

## Alternatives
- Direct promotion at L7 with high reliability: rejected — reliability
  measures execution, not design quality; the sandbox exists because
  contracts fail in ways reliability cannot see.

## Tradeoffs
(+) Every installed capability arrives with: a measured signature, a
  passing sandbox run, a catalog unit with a content hash, and a
  sponsor's spent token. Full provenance, by construction.
(−) Template-derived designs are conservative; genuinely novel agent
  shapes still need human architects (noted as v8 direction).

## Consequences
`test_install_refused_without_sponsorship`,
`test_full_run_with_valid_token_installs`,
`test_failed_sandbox_never_installs`; demo evidence in
`evidence/v7-factory-run.json`.
