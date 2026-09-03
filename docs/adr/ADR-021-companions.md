# ADR-021: Companions — external agents as bounded nodes

**Status: ACCEPTED (v12.0)**

## Context
The best hands in the ecosystem live outside this OS: Pi (the coding
agent the SSSF/fusion-harness lineage runs on) and DeerFlow
(ByteDance's deep-research SuperAgent, which now ships a headless
`--json` CLI). The temptation is to grant them trust byinstalled-by;
the failure mode of every "integrate the agent" story is that the
outside agent arrives with its own laws.

## Decision
Companions are subcontractors: **authority on loan, never law on
loan.** Mechanically:
- Pi is invoked exactly as the factory pattern invokes it —
  `pi -p --mode json --session-id`, prompt in argv, **stdin DEVNULL**
  (their documented lesson: an inherited non-TTY stdin can hang a
  child silently forever).
- The JSONL event stream is observed (capped) into the OS event log;
  redaction is structural.
- **Artifacts derive from the filesystem diff against a pre-call
  checkpoint — never from the agent's self-report.** The final JSON
  object Pi prints is a *claim*; the diff is the fact; gates re-check.
- The writes: boundary applies to companions identically: writes
  outside the globs are reverted and the phase dies.
- Wall-clock timeout kills hangs; a missing binary fails structurally
  ("the OS will not guess"); no companion is ever auto-installed.
- DeerFlow's output is research *input*, not truth: mined sources
  become findings at capped confidence (0.75), the final answer is
  quarantined unverified, and absent/garbage streams yield an empty
  brief — the v5 law, no sources no fabrication.

## Alternatives
- Vendor SDK embedding: rejected — companions are processes, not
  libraries; process boundaries are the cheapest containment we own.
- Trust-on-install (signed companion manifests): a future fast-lane,
  the same way federation's web-of-trust would be — never a
  substitute for the boundary and the diff.

## Tradeoffs
(+) Any CLI agent can become a companion by matching one of the two
  contracts (builder JSONL / researcher NDJSON) — the shape is the
  interface.
(−) Stream schemas are parsed defensively (type/text/content/message
  shapes) rather than from a frozen spec; real Pi/DeerFlow field
  validation remains an operations exercise, honestly noted.

## Consequences
`test_good_pi_produces_gated_envelope`,
`test_roguish_pi_is_reverted_and_killed`,
`test_hanging_pi_dies_at_wall_clock`,
`test_garbage_stream_yields_empty_brief`,
`test_deerflow_handler_end_to_end` — all against fake executables:
the integration is proven without installs, keys, or spend.
