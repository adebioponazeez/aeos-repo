# ADR-006: Checkpoints + harness-enforced write boundaries

**Status: ACCEPTED (v0.5)**

## Context
SSSF rule 9: `tools:` is a capability list; `writes:` is the boundary
— because `bash` can do anything, a tool list can never make "this
agent changes nothing" true. Enforcement must be mechanical and
post-hoc.

## Decision
Before every writing handler: a full-fidelity snapshot (copy-on-write
map of the workspace). After: diff the tree — files changed or created
outside the agent's `writes:` globs are reverted and the phase dies
with a `boundary.violation` event. `.aeos/` is always writable: system
state lives inside the fence, agents stay outside it. `rollback(cp)`
restores the full tree for destructive recovery.

## Alternatives considered
- **Git-as-checkpoint** (the strong 2026 pattern at repo scale):
correct, and planned for v2; v1.0 needed workspace-portable semantics
that also work in scratch directories and sandboxes without repos.

## Tradeoffs
(+) Unauthorized writes are impossible to keep — by construction.
(−) Full snapshots cost O(workspace) per phase; fine at this scale,
explicitly noted for v2.

## Consequences
The boundary is real because it is enforced by code the agent cannot
touch. Proven by `test_unauthorized_writes_are_reverted`.
