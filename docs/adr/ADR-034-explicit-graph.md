# ADR-034: The graph is explicit, cycles fail closed

**Status: ACCEPTED (v25.0)**

## Context
CrewAI has crews, LangGraph has graphs; our waves were implicit.
Implicit graphs hide cycles and skip-logic until they bite.

## Decision
`Colony` — declarative DAG: nodes declare `requires` edges and
optional `condition` gates; wave execution in dependency order; ctx
carries every output. Failures block dependents EARLY; skipped or
failed dependencies block too; unreachable nodes (cycles) end
BLOCKED — the colony NEVER hangs (no-progress break + max_waves).
Every transition is an event on the bus. Skips are DEGRADED, not OK:
a colony that did not run its declared graph says so.

## Alternatives
Emergent/swarm delegation: rejected as default — non-deterministic
routing is untestable by our charter.

## Consequences
`test_cycles_block_instead_of_hanging`,
`test_failure_blocks_dependents_fail_closed`,
`test_condition_gate_skips_cleanly`.
