# ADR-033: Expose only verbs that read

**Status: ACCEPTED (v24.0)**

## Context
v21 made us an MCP client; the ecosystem also expects AEOS to be
callable. A server that mutates on a remote caller's word is a
boundary hole with a protocol logo on it.

## Decision
`mcp_server.py` — symmetric JSON-RPC server (`python -m
aeos.mcp_server`), same framing as the client. Three tools:
leverage_audit, standards_check, recall. THE LAW: `READONLY_TOOLS`
is the complete tool set — the server exposes verbs that READ,
never verbs that WRITE; the equality is a test. Unknown methods
error (-32601); internal errors fail closed as -32602, never a
crash. Proven by roundtrip against our own v21 client. `otel.py` in
the same version: the fleet stream exported as OTel-style spans,
content-addressed ids, byte-stable, FAILED→ERROR.

## Consequences
`test_tools_listed_and_all_readonly`, `test_real_interop_with_v21_client`,
`test_export_is_byte_stable`.
