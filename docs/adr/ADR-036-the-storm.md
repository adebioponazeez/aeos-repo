# ADR-036: Chaos is a first-class command

**Status: ACCEPTED (v27.0)**

## Context
Resilience claims without chaos receipts are marketing. The user's
challenge: prove it under hostile conditions — power cuts, full
disks, garbage inputs, no network, constrained hardware.

## Decision
`storm.py` + `aeos storm`: eight END-TO-END scenarios on the real
system (real subprocesses, real SIGKILLs, no mocks where reality is
affordable): kill -9 storm x3 + recovery; torn power-cut files;
disk-full at the bundle write (prior evidence byte-intact); garbage
intents; TOTAL socket blackout; full run under RLIMIT_AS=256MB;
concurrent runs refused by the lock; companion server killed
mid-session (found and fixed a real leak: BrokenPipeError now fails
closed as MCPError). A scenario passes only if the system fails
closed or recovers — never crashes, never corrupts.

## Consequences
`test_every_scenario_survives` (8/8), plus the storm runs inside
the standard suite on every `pytest` — the receipts cannot rot.
