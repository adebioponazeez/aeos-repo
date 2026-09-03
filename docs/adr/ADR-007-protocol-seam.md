# ADR-007: MCP/A2A are adapters, not assumptions

**Status: ACCEPTED (v1.0) — seam defined, adapters not shipped**

## Context
MCP is vendor-neutral under the Agentic AI Foundation (Linux
Foundation), with the 2026-07 stateless-core release candidate, Server
Cards discovery, and SEP-2085's untrusted-by-default tool validation.
A2A covers remote agent-to-agent delegation. Protocol churn is
guaranteed; the OS core must not chase it.

## Decision
Tool and remote-agent integration lands at the handler seam: a handler
may be in-process (today) or tool-server-backed (tomorrow) without
touching the graph, governor, gates or event log. The OS's own
contracts — envelope, action class, writes — stay protocol-free.

## Alternatives considered
- **Native MCP client in core** — rejected for v1.0: the spec cycle is
mid-flight; coupling now buys rewrite risk later.

## Tradeoffs
(+) Core stays stable through protocol evolution.
(−) v1.0 cannot drive real MCP servers yet — documented, not hidden.

## Consequences
When adapters ship they inherit every guarantee in this repo
unchanged. That is the entire point of the seam.
