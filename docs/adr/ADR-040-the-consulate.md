# ADR-040: The door opens on purpose — and only to readers

**Status: ACCEPTED (v31.0)**

## Context
The final named MCP seam: HTTP *server* mode. The risk with any
wire-facing server is drift — a tool set that grows writes, a bind
that quietly reaches the world.

## Decision
`mcp_http_server.py` — the Consulate: the SAME `handle_request` (one
source of tool law) served over HTTP via ThreadingHTTPServer. The
law, testable on every transport: the tool set is exactly
READONLY_TOOLS; default bind 127.0.0.1 (0.0.0.0 must be explicit);
bodies bounded (1MB); malformed input fails closed as JSON-RPC
errors, never a crash; notifications accepted silently (202). Build
finding, fixed: the v30 client violated JSON-RPC by sending
`notifications/initialized` WITH an id — the strict consulate
refused it, so the client now sends true id-less notifications.
Wire-level roundtrip proven: our HTTP client against our HTTP
server.

## Consequences
`test_serves_readonly_tools_over_http`, `test_default_bind_is_loopback_only`,
`test_malformed_body_fails_closed_server_survives`,
`test_concurrent_requests_all_served`.
