# ADR-030: The protocol is a boundary too

**Status: ACCEPTED (v21.0)**

## Context
MCP is the industry's interop default (native in LangGraph, CrewAI,
Claude Agent SDK, OpenAgents). Two dangers: protocol sprawl, and
trusting a tool because a server vouched for it.

## Decision
`MCPClient` — stdlib JSON-RPC 2.0 over subprocess stdio (the MCP
stdio transport): initialize → tools/list → tools/call. Walls kill
hung servers (select-based timeout); malformed lines fail closed;
`import_tools` marks every imported tool UNTRUSTED — reputation is
not validation (the v9 federation law, protocol edition). A bundled
demo server keeps the client testable offline.

## Alternatives
Official MCP SDKs: rejected as default — dependency weight for a
wire protocol this small; the seam is `MCPClient.request`.

## Consequences
`test_hanging_server_is_killed_by_the_wall`,
`test_garbage_line_fails_closed`,
`test_imported_tools_enter_untrusted`.
