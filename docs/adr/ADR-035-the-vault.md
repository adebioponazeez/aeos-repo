# ADR-035: Power loss loses moments, never memory

**Status: ACCEPTED (v26.0)**

## Context
The audit was honest: a torn line in memory.jsonl crashed the whole
store on load; the flush rewrote the file non-atomically (kill
mid-flush = total amnesia); the bundle write was not atomic; the
fleet replay crashed on torn tails. Green tests in a cozy sandbox
had proven none of this.

## Decision
`vault.py` — the fault-tolerant core every other module now stands
on: `durable_write` (tmp + fsync + rename + dir fsync — a crash or
full disk never touches the original); `load_jsonl_tolerant` +
`quarantine_torn` (torn lines go to a `.torn` sidecar, the system
CONTINUES — forensics kept, never silently lost); `WorkspaceLock`
(fcntl.flock — the KERNEL releases it when the holder dies, so
kill -9 can never strand a workspace); `socket_blackout` (any socket
construction raises — completing a full run inside it proves the
default path is offline); `environment_scan` (read-only host truth;
a scanner that checks the network by using it is a bug). Integrated:
MemoryStore, EventBus, PlanCheckpoint, and the evidence bundle all
write durable and load tolerant.

## Consequences
`test_failed_rename_leaves_original_intact`,
`test_torn_tail_quarantined_not_fatal`,
`test_killed_holder_cannot_strand_the_workspace`,
`test_full_run_makes_zero_socket_calls`.
