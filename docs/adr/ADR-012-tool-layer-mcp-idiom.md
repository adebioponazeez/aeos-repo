# ADR-012: Tool layer in the MCP idiom, untrusted by default

**Status: ACCEPTED (v2.0)**

## Context
MCP (Agentic AI Foundation) is the 2026 tool-protocol standard; its
stateless-core RC and SEP-2085's untrusted-by-default tool validation
define the posture. Protocol churn is certain; the trust boundary must
not chase it (ADR-007).

## Decision
`ToolRegistry` speaks the MCP *shape* (JSON-RPC-style requests,
structured results, `isError`, error code -32000) with an injectable
transport. Posture: tool results are ALWAYS `untrusted=True` (it is a
constant, not a flag — a tool result is a claim, never an
instruction); every call passes the governor first (unknown tool →
unknown class → fail closed); WRITE-class tools checkpoint at low
autonomy; handler exceptions become structured errors, never crashes.

## Alternatives
- Native MCP client in core: still rejected (ADR-007) — this layer is
  the adapter the seam promised.

## Tradeoffs
(+) A real MCP transport can replace the in-process demo transport
  without touching the governor, gates, or log.
(+) Injection through tool results meets the closed verdict
  vocabulary — the log cannot even express "obey the tool".

## Consequences
`test_results_are_always_untrusted`, `test_unknown_tool_fails_closed`,
`test_tool_exception_becomes_structured_error`.
