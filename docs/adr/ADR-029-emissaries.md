# ADR-029: Every emissary, same law

**Status: ACCEPTED (v20.0)**

## Context
The ecosystem's coding agents (aider, headless Claude CLI) each have
their own output habits; a harness that trusts any of them
self-reports has a hole per companion.

## Decision
Round 2 extends the Pi law to every coding emissary: one report
contract rides in the prompt; artifacts are verified against the
filesystem (`verify_against_disk`); phantom artifacts raise; walls
kill (SubprocessRunner, stdin DEVNULL); boundaries revert
(`coding_handler` shared handler shape for aider/claude).

## Consequences
`test_phantom_artifacts_are_detected`,
`test_phantom_companion_raises`,
`test_boundary_violation_is_reverted`,
`test_timeout_yields_not_ok`.
