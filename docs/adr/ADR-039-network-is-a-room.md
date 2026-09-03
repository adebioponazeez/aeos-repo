# ADR-039: Network is a room you enter on purpose

**Status: ACCEPTED (v30.0)**

## Context
Two benchmark seams remained: MCP transports beyond stdio, and OTLP
push to collectors. Both are network features in a system whose
default path is provably offline (v26 blackout receipts) — the
design question is how both coexist with that law.

## Decision
`mcp_http.py` — the streamable-HTTP MCP transport (POST JSON-RPC;
response as JSON or text/event-stream `data:` lines); same client
law: walls on every read, malformed bodies fail closed as MCPError.
`otlp.py` — OTLP/HTTP push with bounded retries (429/5xx only,
backoff), where a hostile wire yields a RECEIPT (ok=False, attempts
named), never an exception and never a hang. Both take an EXPLICIT
endpoint — there is no ambient network anywhere; the default path
stays blackout-proven. Proven on the loopback range: disposable
local servers exercise JSON, SSE, walls, retries, and refusal
without a single external dependency or packet.

## Consequences
`test_the_wall_applies_on_http`, `test_dead_endpoint_fails_closed`,
`test_hostile_wire_is_a_receipt_not_an_exception`,
`test_client_error_is_not_retried`.
