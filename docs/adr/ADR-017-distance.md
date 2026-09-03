# ADR-017: Distance — transports, remote workers, process sandboxes

**Status: ACCEPTED (v8.0)**

## Context
The kernel kept everything in one process on purpose: auditable,
deterministic, testable. Real fleets need distance — models behind
HTTP, tools behind servers, validation in sandboxes that cannot take
the parent down. The risk was that distance would dilute guarantees.

## Decision
Four mechanisms, one rule: *distance changes the transport, never the
truth rules.*
- `HTTPModelTransport` maps wire failures onto the ADR-010 taxonomy
  (503/429→TRANSIENT, timeouts→TRANSIENT, overflow→no-retry).
- `call_remote_tool` returns MCP-shaped results that are **untrusted
  over the wire** — the constant survives geography.
- `WorkerServer`/`RemoteWorker`: A2A-style delegation where a remote
  colleague is indistinguishable from a local handler; broken remote
  handlers become error envelopes, never stack traces.
- `run_isolated()`: sandbox validation in a subprocess with wall-clock
  timeout (parent), CPU/memory rlimits (child, where POSIX provides),
  and a defensive child that always writes a verdict — a sandbox that
  cannot be killed is not a sandbox.

## Alternatives
- Container-per-sandbox: the right production answer at scale;
  in-process supervision is the portable floor beneath it.
- Full A2A protocol adoption: deferred until the spec stabilizes; the
  envelope-over-HTTP shape is the durable part.

## Tradeoffs
(+) Hangs, crashes, and poison inputs die in the child, not the fleet.
(−) Subprocess startup cost per validation (~100ms) — spent only at
promotion time, where it is cheapest.

## Consequences
`test_hanging_candidate_is_killed`, `test_poisoned_input_child_writes_verdict`,
`test_remote_tool_result_untrusted_over_the_wire`, `test_delegation_roundtrips_envelope`.
